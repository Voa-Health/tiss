"""Geração e leitura de mensagens de autorização SP/SADT."""

from __future__ import annotations

import re
from typing import Any

from lxml import etree

from ._lote_codec import hash_epilogo
from ._schema import NS, parser


class AutorizacaoError(ValueError):
    """A mensagem não representa uma autorização SP/SADT."""


_ORDERS: dict[str, tuple[tuple[str, str], ...]] = {
    "transacao": (
        ("sequencial_transacao", "sequencialTransacao"),
        ("data_registro_transacao", "dataRegistroTransacao"),
        ("hora_registro_transacao", "horaRegistroTransacao"),
    ),
    "prestador": (
        ("codigo_prestador_na_operadora", "codigoPrestadorNaOperadora"),
        ("cnpj", "CNPJ"),
        ("cpf", "CPF"),
    ),
    "cabecalho": (
        ("registro_ans", "registroANS"),
        ("numero_guia_prestador", "numeroGuiaPrestador"),
    ),
    "beneficiario": (
        ("numero_carteira", "numeroCarteira"),
        ("atendimento_rn", "atendimentoRN"),
        ("tipo_ident", "tipoIdent"),
        ("identificador_beneficiario", "identificadorBeneficiario"),
    ),
    "contratado": (
        ("codigo_prestador_na_operadora", "codigoPrestadorNaOperadora"),
        ("cpf_contratado", "cpfContratado"),
        ("cnpj_contratado", "cnpjContratado"),
    ),
    "executante": (
        ("codigo_prestador_na_operadora", "codigonaOperadora"),
        ("cnes", "CNES"),
    ),
    "profissional": (
        ("nome_profissional", "nomeProfissional"),
        ("conselho_profissional", "conselhoProfissional"),
        ("numero_conselho_profissional", "numeroConselhoProfissional"),
        ("uf", "UF"),
        ("cbos", "CBOS"),
    ),
    "dados_solicitante": (
        ("contratado_solicitante", "contratadoSolicitante"),
        ("nome_contratado_solicitante", "nomeContratadoSolicitante"),
        ("profissional_solicitante", "profissionalSolicitante"),
    ),
    "procedimento": (
        ("codigo_tabela", "codigoTabela"),
        ("codigo_procedimento", "codigoProcedimento"),
        ("descricao_procedimento", "descricaoProcedimento"),
    ),
    "item_solicitado": (
        ("procedimento", "procedimento"),
        ("quantidade_solicitada", "quantidadeSolicitada"),
    ),
    "solicitacao": (
        ("cabecalho_solicitacao", "cabecalhoSolicitacao"),
        ("numero_guia_principal", "numeroGuiaPrincipal"),
        ("ausencia_cod_validacao", "ausenciaCodValidacao"),
        ("cod_validacao", "codValidacao"),
        ("tipo_etapa_autorizacao", "tipoEtapaAutorizacao"),
        ("dados_beneficiario", "dadosBeneficiario"),
        ("dados_solicitante", "dadosSolicitante"),
        ("carater_atendimento", "caraterAtendimento"),
        ("data_solicitacao", "dataSolicitacao"),
        ("indicacao_clinica", "indicacaoClinica"),
        ("cobertura_especial", "coberturaEspecial"),
        ("procedimentos_solicitados", "procedimentosSolicitados"),
        ("dados_executante", "dadosExecutante"),
        ("observacao", "observacao"),
    ),
    "dados_autorizacao": (
        ("numero_guia_prestador", "numeroGuiaPrestador"),
        ("numero_guia_operadora", "numeroGuiaOperadora"),
        ("ausencia_cod_validacao", "ausenciaCodValidacao"),
        ("cod_validacao", "codValidacao"),
        ("data_autorizacao", "dataAutorizacao"),
        ("senha", "senha"),
        ("data_validade_senha", "dataValidadeSenha"),
    ),
    "procedimento_autorizado": (
        ("sequencial_item", "sequencialItem"),
        ("procedimento", "procedimento"),
        ("quantidade_solicitada", "quantidadeSolicitada"),
        ("quantidade_autorizada", "quantidadeAutorizada"),
        ("valor_solicitado", "valorSolicitado"),
        ("valor_autorizado", "valorAutorizado"),
        ("opcao_fabricante", "opcaoFabricante"),
        ("registro_anvisa", "registroANVISA"),
        ("codigo_ref_fabricante", "codigoRefFabricante"),
        ("autorizacao_funcionamento", "autorizacaoFuncionamento"),
        ("motivos_negativa", "motivosNegativa"),
    ),
    "motivo_negativa": (
        ("codigo_glosa", "codigoGlosa"),
        ("descricao_glosa", "descricaoGlosa"),
    ),
    "prestador_autorizado": (
        ("dados_contratado", "dadosContratado"),
        ("cnes_contratado", "cnesContratado"),
    ),
    "autorizacao": (
        ("dados_autorizacao", "dadosAutorizacao"),
        ("tipo_etapa_autorizacao", "tipoEtapaAutorizacao"),
        ("dados_beneficiario", "dadosBeneficiario"),
        ("nome_beneficiario", "nomeBeneficiario"),
        ("nome_social_beneficiario", "nomeSocialBeneficiario"),
        ("cobertura_especial", "coberturaEspecial"),
        ("prestador_autorizado", "prestadorAutorizado"),
        ("status_solicitacao", "statusSolicitacao"),
        ("motivos_negativa", "motivosNegativa"),
        ("servicos_autorizados", "servicosAutorizados"),
        ("observacao", "observacao"),
    ),
}
_NESTED = {
    ("solicitacao", "cabecalho_solicitacao"): "cabecalho",
    ("solicitacao", "dados_beneficiario"): "beneficiario",
    ("solicitacao", "dados_solicitante"): "dados_solicitante",
    ("dados_solicitante", "contratado_solicitante"): "contratado",
    ("dados_solicitante", "profissional_solicitante"): "profissional",
    ("item_solicitado", "procedimento"): "procedimento",
    ("solicitacao", "dados_executante"): "executante",
    ("autorizacao", "dados_autorizacao"): "dados_autorizacao",
    ("autorizacao", "dados_beneficiario"): "beneficiario",
    ("autorizacao", "prestador_autorizado"): "prestador_autorizado",
    ("prestador_autorizado", "dados_contratado"): "contratado",
    ("procedimento_autorizado", "procedimento"): "procedimento",
    ("procedimento_autorizado", "motivos_negativa"): "motivo_negativa",
}
_LISTS: dict[tuple[str, str], tuple[str, str, bool, bool]] = {
    ("solicitacao", "procedimentos_solicitados"): (
        "procedimentosSolicitados",
        "item_solicitado",
        False,
        False,
    ),
    ("autorizacao", "motivos_negativa"): ("codigoGlosa", "", True, True),
    ("autorizacao", "servicos_autorizados"): (
        "servicoAutorizado",
        "procedimento_autorizado",
        True,
        False,
    ),
    ("procedimento_autorizado", "motivos_negativa"): (
        "motivoNegativa",
        "motivo_negativa",
        True,
        False,
    ),
}
_TAGS = {(kind, key): tag for kind, order in _ORDERS.items() for key, tag in order}
_REQUEST_PATH = ("prestadorParaOperadora", "solicitacaoProcedimento", "solicitacaoSP-SADT")
_RESPONSE_PATH = ("operadoraParaPrestador", "autorizacaoServicos", "autorizacaoServico")


def _append_object(parent: etree._Element, data: Any, kind: str) -> None:
    if not isinstance(data, dict):
        raise AutorizacaoError(f"{kind} deve ser um objeto")
    allowed = {key for key, _ in _ORDERS[kind]}
    unknown = data.keys() - allowed
    if unknown:
        raise AutorizacaoError(f"Campo desconhecido em {kind}: {sorted(unknown)[0]}")
    for key, tag in _ORDERS[kind]:
        if key not in data:
            continue
        value = data[key]
        if value is None:
            continue
        list_spec = _LISTS.get((kind, key))
        child_kind = _NESTED.get((kind, key))
        if list_spec:
            item_tag, item_kind, wrapped, scalar = list_spec
            if not isinstance(value, list):
                raise AutorizacaoError(f"{key} deve ser uma lista")
            container = etree.SubElement(parent, f"{{{NS}}}{tag}") if wrapped else parent
            for item in value:
                node = etree.SubElement(container, f"{{{NS}}}{item_tag}")
                if scalar:
                    node.text = str(item)
                else:
                    _append_object(node, item, item_kind)
        else:
            node = etree.SubElement(parent, f"{{{NS}}}{tag}")
            if child_kind:
                _append_object(node, value, child_kind)
            elif isinstance(value, (dict, list)):
                raise AutorizacaoError(f"{key} deve ser um valor simples")
            else:
                node.text = str(value)


def _path_node(root: etree._Element, path: tuple[str, ...]) -> etree._Element:
    node = root
    for name in path:
        node = etree.SubElement(node, f"{{{NS}}}{name}")
    return node


def _document(message: Any) -> tuple[etree._Element, str]:
    if not isinstance(message, dict):
        raise AutorizacaoError("Mensagem deve ser um objeto")
    allowed = {"versao", "transacao", "prestador", "operadora", "solicitacao", "autorizacao"}
    unknown = message.keys() - allowed
    if unknown:
        raise AutorizacaoError(f"Campo desconhecido: {sorted(unknown)[0]}")
    bodies = [key for key in ("solicitacao", "autorizacao") if key in message]
    if len(bodies) != 1:
        raise AutorizacaoError("Informe exatamente um dos campos 'solicitacao' ou 'autorizacao'.")
    if message.get("versao") != "4.03.00":
        raise AutorizacaoError("Autorização aceita somente a versão 4.03.00")
    if not isinstance(message.get("operadora"), dict):
        raise AutorizacaoError("operadora deve ser um objeto")
    if set(message["operadora"]) != {"registro_ans"}:
        raise AutorizacaoError("operadora deve conter somente registro_ans")
    if not isinstance(message.get("prestador"), dict):
        raise AutorizacaoError("prestador deve ser um objeto")
    identity = {"codigo_prestador_na_operadora", "cnpj", "cpf"} & message["prestador"].keys()
    if len(identity) != 1:
        raise AutorizacaoError("prestador deve conter exatamente uma identificação")
    if not isinstance(message.get("transacao"), dict):
        raise AutorizacaoError("transacao deve ser um objeto")
    body = bodies[0]
    root = etree.Element(f"{{{NS}}}mensagemTISS", nsmap={"ans": NS})
    header = etree.SubElement(root, f"{{{NS}}}cabecalho")
    identification = etree.SubElement(header, f"{{{NS}}}identificacaoTransacao")
    transaction_type = (
        "SOLICITACAO_PROCEDIMENTOS" if body == "solicitacao" else "RESPOSTA_SOLICITACAO"
    )
    etree.SubElement(identification, f"{{{NS}}}tipoTransacao").text = transaction_type
    _append_object(identification, message.get("transacao", {}), "transacao")
    origin = etree.SubElement(header, f"{{{NS}}}origem")
    destination = etree.SubElement(header, f"{{{NS}}}destino")
    if body == "solicitacao":
        provider_node = etree.SubElement(origin, f"{{{NS}}}identificacaoPrestador")
        _append_object(provider_node, message.get("prestador", {}), "prestador")
        etree.SubElement(destination, f"{{{NS}}}registroANS").text = str(
            message.get("operadora", {}).get("registro_ans", "")
        )
        message_node = _path_node(root, _REQUEST_PATH)
    else:
        etree.SubElement(origin, f"{{{NS}}}registroANS").text = str(
            message.get("operadora", {}).get("registro_ans", "")
        )
        provider_node = etree.SubElement(destination, f"{{{NS}}}identificacaoPrestador")
        _append_object(provider_node, message.get("prestador", {}), "prestador")
        message_node = _path_node(root, _RESPONSE_PATH)
    etree.SubElement(header, f"{{{NS}}}Padrao").text = "4.03.00"
    _append_object(message_node, message[body], body)
    epilogue = etree.SubElement(root, f"{{{NS}}}epilogo")
    etree.SubElement(epilogue, f"{{{NS}}}hash").text = ""
    return root, body


def build_autorizacao(mensagem: dict[str, Any]) -> bytes:
    """Gera XML de autorização SP/SADT com hash do epílogo."""
    root, _ = _document(mensagem)
    hash_node = root[-1][0]
    try:
        empty_hash_xml = bytes(
            etree.tostring(
                root,
                encoding="ISO-8859-1",
                xml_declaration=True,
                pretty_print=False,
            )
        )
    except (UnicodeEncodeError, ValueError) as exc:
        raise AutorizacaoError("Mensagem contém caracteres incompatíveis com ISO-8859-1") from exc
    hash_node.text = hash_epilogo(empty_hash_xml)
    return bytes(
        etree.tostring(
            root,
            encoding="ISO-8859-1",
            xml_declaration=True,
            pretty_print=False,
        )
    )


def _xml_bytes(xml: bytes | str) -> bytes:
    if isinstance(xml, bytes):
        return xml
    match = re.search(r"""encoding=["']([^"']+)["']""", xml[:100], flags=re.IGNORECASE)
    encoding = match.group(1) if match else "utf-8"
    return xml.encode(encoding)


def _parse_object(
    parent: etree._Element, kind: str, *, ignored: set[str] | None = None
) -> dict[str, Any]:
    fields = {tag: (key, tag) for key, tag in _ORDERS[kind]}
    ignored = ignored or set()
    known = set(fields) | ignored
    result: dict[str, Any] = {}
    for child in parent:
        if not isinstance(child.tag, str):
            continue
        tag = etree.QName(child).localname
        if tag not in known:
            raise AutorizacaoError(f"Elemento desconhecido em {kind}: {tag}")
        if tag in ignored:
            continue
        key, _ = fields[tag]
        list_spec = _LISTS.get((kind, key))
        child_kind = _NESTED.get((kind, key))
        if list_spec:
            item_tag, item_kind, wrapped, scalar = list_spec
            container = child if wrapped else parent
            if not wrapped and tag != item_tag:
                continue
            items = [
                item
                for item in container
                if isinstance(item.tag, str) and etree.QName(item).localname == item_tag
            ]
            result[key] = [
                (item.text or "").strip() if scalar else _parse_object(item, item_kind)
                for item in items
            ]
        elif child_kind:
            result[key] = _parse_object(child, child_kind)
        else:
            result[key] = (child.text or "").strip()
    return result


def _required_child(parent: etree._Element, name: str) -> etree._Element:
    result = next(
        (
            child
            for child in parent
            if isinstance(child.tag, str) and etree.QName(child).localname == name
        ),
        None,
    )
    if result is None:
        raise AutorizacaoError(f"Elemento ausente: {name}")
    return result


def _parse_header_provider(node: etree._Element) -> dict[str, Any]:
    mapping = {
        "codigoPrestadorNaOperadora": "codigo_prestador_na_operadora",
        "CNPJ": "cnpj",
        "CPF": "cpf",
    }
    children = [child for child in node if isinstance(child.tag, str)]
    if len(children) > 1:
        raise AutorizacaoError("Identificação do prestador inválida")
    if not children:
        return {}
    tag = etree.QName(children[0]).localname
    if tag not in mapping:
        raise AutorizacaoError(f"Identificação do prestador desconhecida: {tag}")
    return {mapping[tag]: (children[0].text or "").strip()}


def parse_autorizacao(xml: bytes | str) -> dict[str, Any]:
    """Interpreta XML de solicitação ou resposta de autorização SP/SADT."""
    try:
        raw = _xml_bytes(xml)
        root = etree.fromstring(raw, parser())
    except (etree.XMLSyntaxError, ValueError, TypeError, UnicodeEncodeError) as exc:
        raise AutorizacaoError("XML de autorização inválido") from exc
    if etree.QName(root).localname != "mensagemTISS":
        raise AutorizacaoError("XML não é uma mensagem TISS")
    header = _required_child(root, "cabecalho")
    identification = _required_child(header, "identificacaoTransacao")
    transaction_type = (_required_child(identification, "tipoTransacao").text or "").strip()
    if transaction_type == "SOLICITACAO_PROCEDIMENTOS":
        body = "solicitacao"
        path = _REQUEST_PATH
    elif transaction_type == "RESPOSTA_SOLICITACAO":
        body = "autorizacao"
        path = _RESPONSE_PATH
    else:
        raise AutorizacaoError("Tipo de transação não é uma autorização SP/SADT")
    transaction = _parse_object(identification, "transacao", ignored={"tipoTransacao"})
    origin = _required_child(header, "origem")
    destination = _required_child(header, "destino")
    if body == "solicitacao":
        provider = _parse_header_provider(_required_child(origin, "identificacaoPrestador"))
        ans = _required_child(destination, "registroANS")
    else:
        provider = _parse_header_provider(_required_child(destination, "identificacaoPrestador"))
        ans = _required_child(origin, "registroANS")
    standard = (_required_child(header, "Padrao").text or "").strip()
    if standard != "4.03.00":
        raise AutorizacaoError("parse_autorizacao aceita somente a versão 4.03.00")
    parent = root
    for name in path:
        parent = _required_child(parent, name)
    result: dict[str, Any] = {
        "versao": standard,
        "transacao": transaction,
        "prestador": provider,
        "operadora": {"registro_ans": (ans.text or "").strip()},
        body: _parse_object(parent, body),
    }
    hash_epilogo(raw)
    return result


__all__ = ["AutorizacaoError", "build_autorizacao", "parse_autorizacao"]
