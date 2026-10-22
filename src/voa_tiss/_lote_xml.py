"""Construção ordenada de elementos XML para lotes TISS."""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from lxml import etree

from ._lote import _LIST_TAGS, _MONEY, _ORDERS, _TAGS, Lote, LoteError
from ._schema import NS


def _tag(name: str) -> str:
    return _TAGS.get(
        name,
        "".join(part if index == 0 else part.title() for index, part in enumerate(name.split("_"))),
    )


def _snake(name: str) -> str:
    if name in {"CBOS", "CBO", "UF", "CNES", "CNPJ", "CPF", "ANS"}:
        return name.lower()
    first = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first).lower()


def _pointer(parent: str, key: str | int) -> str:
    escaped = str(key).replace("~", "~0").replace("/", "~1")
    return f"{parent}/{escaped}"


def _ordered(data: Mapping[str, Any], kind: str) -> list[tuple[str, Any]]:
    order = _ORDERS.get(kind, ())
    return sorted(
        data.items(),
        key=lambda item: (order.index(item[0]) if item[0] in order else len(order), item[0]),
    )


def _element(
    parent: etree._Element,
    name: str,
    value: Any,
    pointer: str,
    paths: dict[int, str],
    *,
    kind: str = "",
) -> etree._Element:
    child = etree.SubElement(parent, f"{{{NS}}}{_tag(name)}")
    paths[id(child)] = pointer
    if isinstance(value, dict):
        for key, nested in _ordered(value, kind or name):
            _element(child, key, nested, _pointer(pointer, key), paths, kind=key)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            item_name = _LIST_TAGS.get(name, name[:-1] if name.endswith("s") else name)
            _element(
                child,
                item_name,
                nested,
                _pointer(pointer, index),
                paths,
                kind=_snake(item_name),
            )
    elif value is not None:
        if name in _MONEY:
            try:
                amount = Decimal(str(value)) / Decimal(100)
            except InvalidOperation as exc:
                raise LoteError(f"Valor monetário inválido em {pointer}") from exc
            child.text = f"{amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
        else:
            child.text = str(value)
    return child


def _money_to_cents(text: str) -> int:
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise LoteError("Valor monetário inválido no XML") from exc
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _parse_element(element: etree._Element) -> Any:
    children = [child for child in element if isinstance(child.tag, str)]
    if not children:
        value = element.text or ""
        if _snake(etree.QName(element).localname) in _MONEY:
            return _money_to_cents(value.strip())
        return value.strip()
    result: dict[str, Any] = {}
    for child in children:
        key = _snake(etree.QName(child).localname)
        value = _parse_element(child)
        if key in result:
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(value)
        else:
            result[key] = value
    return result


def _required_lote(lote: Any) -> None:
    if not isinstance(lote, dict):
        raise LoteError("Lote deve ser um objeto")
    required = {"versao", "transacao", "prestador", "operadora", "numero_lote", "guias"}
    if not required <= lote.keys():
        raise LoteError("Lote incompleto")
    if lote.get("versao") != "4.03.00":
        raise LoteError("build_lote aceita somente a versão 4.03.00")
    if not isinstance(lote["transacao"], dict) or not isinstance(lote["prestador"], dict):
        raise LoteError("Transação e prestador devem ser objetos")
    if not isinstance(lote["operadora"], dict) or not isinstance(lote["guias"], list):
        raise LoteError("Operadora deve ser objeto e guias uma lista")
    for guia in lote["guias"]:
        if not isinstance(guia, dict) or guia.get("tipo") not in {"consulta", "sp_sadt"}:
            raise LoteError("Tipo de guia inválido")


def _document(lote: Lote) -> tuple[etree._Element, dict[int, str]]:
    _required_lote(lote)
    root = etree.Element(f"{{{NS}}}mensagemTISS", nsmap={"ans": NS})
    paths: dict[int, str] = {id(root): ""}
    header = etree.SubElement(root, f"{{{NS}}}cabecalho")
    transaction = etree.SubElement(header, f"{{{NS}}}identificacaoTransacao")
    etree.SubElement(transaction, f"{{{NS}}}tipoTransacao").text = "ENVIO_LOTE_GUIAS"
    for name, value in _ordered(lote["transacao"], "transacao"):
        _element(transaction, name, value, _pointer("/transacao", name), paths)
    origin = etree.SubElement(header, f"{{{NS}}}origem")
    provider = etree.SubElement(origin, f"{{{NS}}}identificacaoPrestador")
    for name, value in _ordered(lote["prestador"], "prestador"):
        _element(provider, name, value, _pointer("/prestador", name), paths)
    destination = etree.SubElement(header, f"{{{NS}}}destino")
    _element(
        destination,
        "registro_ans",
        lote["operadora"]["registro_ans"],
        "/operadora/registro_ans",
        paths,
    )
    _element(header, "padrao", lote["versao"], "/versao", paths)
    provider_message = etree.SubElement(root, f"{{{NS}}}prestadorParaOperadora")
    lot = etree.SubElement(provider_message, f"{{{NS}}}loteGuias")
    _element(lot, "numero_lote", lote["numero_lote"], "/numero_lote", paths)
    guides = etree.SubElement(lot, f"{{{NS}}}guiasTISS")
    for index, guide in enumerate(lote["guias"]):
        kind = guide["tipo"]
        tag = "guiaConsulta" if kind == "consulta" else "guiaSP-SADT"
        node = etree.SubElement(guides, f"{{{NS}}}{tag}")
        pointer = _pointer("/guias", index)
        paths[id(node)] = pointer
        if kind == "consulta":
            section = guide.get("cabecalho_consulta", guide.get("cabecalho_guia", {}))
            _element(
                node,
                "cabecalho_consulta",
                section,
                _pointer(pointer, "cabecalho_consulta"),
                paths,
                kind="cabecalho_guia",
            )
        elif "cabecalho_guia" in guide:
            _element(
                node,
                "cabecalho_guia",
                guide["cabecalho_guia"],
                _pointer(pointer, "cabecalho_guia"),
                paths,
                kind="cabecalho_guia",
            )
        for name, value in _ordered(
            {
                k: v
                for k, v in guide.items()
                if k not in {"tipo", "cabecalho_consulta", "cabecalho_guia"}
            },
            "guia",
        ):
            kind_name = (
                "dados_atendimento_consulta"
                if kind == "consulta" and name == "dados_atendimento"
                else name
            )
            _element(node, name, value, _pointer(pointer, name), paths, kind=kind_name)
    epilogue = etree.SubElement(root, f"{{{NS}}}epilogo")
    etree.SubElement(epilogue, f"{{{NS}}}hash").text = ""
    return root, paths
