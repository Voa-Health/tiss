"""Leitura, geração e hash de epílogo XML de lotes."""

from __future__ import annotations

import hashlib
from typing import Any, Literal, cast

from lxml import etree

from ._lote import Guia, Lote, LoteError
from ._lote_xml import _document, _parse_element, _snake
from ._schema import parser


def hash_epilogo(xml: bytes | str) -> str:
    """Calcula o digest do epílogo ANS na ordem dos textos folha."""
    raw = xml.encode("ISO-8859-1") if isinstance(xml, str) else xml
    try:
        root = etree.fromstring(raw, parser())
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise LoteError("XML inválido para calcular o hash") from exc
    # Comentários XML não são elementos; o digest usa bytes ISO-8859-1.
    text = "".join(element.text or "" for element in _hash_leaves(root))
    try:
        encoded = text.encode("ISO-8859-1")
    except UnicodeEncodeError as exc:
        raise LoteError("Texto fora da codificação ISO-8859-1") from exc
    return hashlib.md5(encoded).hexdigest()


def _hash_leaves(root: etree._Element) -> list[etree._Element]:
    leaves = []
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        if etree.QName(element).localname == "hash":
            continue
        ancestor = element.getparent()
        inside_epilogue = False
        while ancestor is not None:
            if isinstance(ancestor.tag, str) and etree.QName(ancestor).localname == "epilogo":
                inside_epilogue = True
                break
            ancestor = ancestor.getparent()
        if not inside_epilogue and not any(isinstance(child.tag, str) for child in element):
            leaves.append(element)
    return leaves


def build_lote(lote: Lote) -> bytes:
    """Gera XML TISS 4.03.00 determinístico com hash do epílogo."""
    root, _ = _document(lote)
    epilogue_hash = hashlib.md5(
        "".join(element.text or "" for element in _hash_leaves(root)).encode("ISO-8859-1")
    ).hexdigest()
    root[-1][0].text = epilogue_hash
    try:
        return bytes(
            etree.tostring(
                root,
                encoding="ISO-8859-1",
                xml_declaration=True,
                pretty_print=False,
            )
        )
    except (UnicodeEncodeError, ValueError) as exc:
        raise LoteError("Lote contém caracteres incompatíveis com ISO-8859-1") from exc


def _first(element: etree._Element, name: str) -> etree._Element | None:
    return next(
        (
            child
            for child in element.iter()
            if isinstance(child.tag, str) and etree.QName(child).localname == name
        ),
        None,
    )


def parse_lote(xml: bytes | str) -> Lote:
    """Interpreta XML de lote TISS 4.03.00 no modelo JSON público."""
    raw = xml.encode("ISO-8859-1") if isinstance(xml, str) else xml
    try:
        root = etree.fromstring(raw, parser())
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise LoteError("XML de lote inválido") from exc
    if etree.QName(root).localname != "mensagemTISS":
        raise LoteError("XML não é uma mensagem TISS")
    padrao = _first(root, "Padrao")
    if padrao is None or (padrao.text or "").strip() != "4.03.00":
        raise LoteError("parse_lote aceita somente a versão 4.03.00")
    header = _first(root, "cabecalho")
    message = _first(root, "prestadorParaOperadora")
    if header is None or message is None:
        raise LoteError("XML não contém um lote de prestador")
    transaction = _first(header, "identificacaoTransacao")
    provider = _first(header, "identificacaoPrestador")
    destination = _first(header, "destino")
    ans = _first(destination, "registroANS") if destination is not None else None
    lot = _first(message, "loteGuias")
    lot_number = _first(lot, "numeroLote") if lot is not None else None
    guide_container = _first(lot, "guiasTISS") if lot is not None else None
    if (
        transaction is None
        or provider is None
        or ans is None
        or lot_number is None
        or guide_container is None
    ):
        raise LoteError("Cabeçalho do lote incompleto")
    transaction_values = _parse_element(transaction)
    transaction_values.pop("tipo_transacao", None)
    provider_values = _parse_element(provider)
    guides: list[Guia] = []
    for node in guide_container:
        if not isinstance(node.tag, str):
            continue
        tag = etree.QName(node).localname
        if tag not in {"guiaConsulta", "guiaSP-SADT"}:
            raise LoteError(f"Tipo de guia não suportado: {tag}")
        kind: Literal["consulta", "sp_sadt"] = "consulta" if tag == "guiaConsulta" else "sp_sadt"
        guide: dict[str, Any] = {"tipo": kind}
        header_name = "cabecalhoConsulta" if kind == "consulta" else "cabecalhoGuia"
        for section in node:
            if not isinstance(section.tag, str):
                continue
            local = etree.QName(section).localname
            key = _snake(local)
            if local == header_name:
                if kind == "consulta":
                    guide["cabecalho_consulta"] = _parse_element(section)
                else:
                    guide["cabecalho_guia"] = _parse_element(section)
            elif local == "procedimentosExecutados":
                items = [
                    _parse_element(child)
                    for child in section
                    if isinstance(child.tag, str)
                    and etree.QName(child).localname == "procedimentoExecutado"
                ]
                guide["procedimentos_executados"] = items
            else:
                guide[key] = _parse_element(section)
        guides.append(cast(Guia, guide))
    result: Lote = {
        "versao": "4.03.00",
        "transacao": transaction_values,
        "prestador": provider_values,
        "operadora": {"registro_ans": (ans.text or "").strip()},
        "numero_lote": (lot_number.text or "").strip(),
        "guias": guides,
    }
    return result


def json_schema() -> dict[str, Any]:
    """Retorna o esquema JSON do lote."""
    string = {"type": "string"}
    money = {"type": "integer"}
    item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "sequencial_item": string,
            "data_execucao": string,
            "hora_inicial": string,
            "hora_final": string,
            "procedimento": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "codigo_tabela": string,
                    "codigo_procedimento": string,
                    "descricao_procedimento": string,
                },
            },
            "quantidade_executada": string,
            "via_acesso": string,
            "tecnica_utilizada": string,
            "reducao_acrescimo": string,
            "valor_unitario": money,
            "valor_total": money,
        },
    }
    section_properties = {
        "cabecalho_guia": {
            "registro_ans": string,
            "numero_guia_prestador": string,
            "numero_guia_operadora": string,
            "guia_principal": string,
        },
        "cabecalho_consulta": {
            "registro_ans": string,
            "numero_guia_prestador": string,
            "numero_guia_operadora": string,
        },
        "dados_beneficiario": {
            "numero_carteira": string,
            "atendimento_rn": string,
            "nome_beneficiario": string,
        },
        "dados_solicitante": {
            "contratado_solicitante": {"type": "object"},
            "nome_contratado_solicitante": string,
            "profissional_solicitante": {"type": "object"},
        },
        "dados_solicitacao": {
            "data_solicitacao": string,
            "carater_atendimento": string,
            "indicacao_clinica": string,
        },
        "dados_executante": {"type": "object"},
        "contratado_executante": {"type": "object"},
        "profissional_executante": {"type": "object"},
        "indicacao_acidente": string,
        "dados_atendimento": {
            "cobertura_especial": string,
            "regime_atendimento": string,
            "saude_ocupacional": string,
            "data_atendimento": string,
            "tipo_consulta": string,
            "procedimento": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "codigo_tabela": string,
                    "codigo_procedimento": string,
                    "valor_procedimento": money,
                },
            },
            "tipo_atendimento": string,
        },
        "procedimentos_executados": {"type": "array", "items": item},
        "valor_total": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                name: money
                for name in (
                    "valor_procedimentos",
                    "valor_diarias",
                    "valor_taxas",
                    "valor_materiais",
                    "valor_opme",
                    "valor_medicamentos",
                    "valor_gases_medicinais",
                    "valor_total_geral",
                )
            },
        },
        "numero_guia_operadora": string,
        "ausencia_cod_validacao": string,
        "cod_validacao": string,
        "observacao": string,
    }
    guide: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["tipo"],
        "properties": {
            "tipo": {"enum": ["consulta", "sp_sadt"]},
            **{
                name: {
                    "type": "array" if name == "procedimentos_executados" else "object",
                    "items": schema["items"]
                    if isinstance(schema, dict) and "items" in schema
                    else {},
                    "additionalProperties": False,
                    "properties": properties if isinstance(properties, dict) else {},
                }
                if name
                not in {
                    "indicacao_acidente",
                    "numero_guia_operadora",
                    "ausencia_cod_validacao",
                    "cod_validacao",
                    "observacao",
                }
                else properties
                for name, properties in section_properties.items()
                for schema in [properties]
            },
        },
    }
    for key in (
        "indicacao_acidente",
        "numero_guia_operadora",
        "ausencia_cod_validacao",
        "cod_validacao",
        "observacao",
    ):
        guide["properties"][key] = string
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Lote TISS 4.03.00",
        "type": "object",
        "additionalProperties": False,
        "required": ["versao", "transacao", "prestador", "operadora", "numero_lote", "guias"],
        "properties": {
            "versao": {"const": "4.03.00"},
            "transacao": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "sequencial_transacao",
                    "data_registro_transacao",
                    "hora_registro_transacao",
                ],
                "properties": {
                    "sequencial_transacao": string,
                    "data_registro_transacao": string,
                    "hora_registro_transacao": string,
                },
            },
            "prestador": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "cnpj": string,
                    "cpf": string,
                    "codigo_prestador_na_operadora": string,
                },
                "minProperties": 1,
                "maxProperties": 1,
            },
            "operadora": {
                "type": "object",
                "additionalProperties": False,
                "required": ["registro_ans"],
                "properties": {"registro_ans": string},
            },
            "numero_lote": string,
            "guias": {"type": "array", "items": guide},
        },
    }
