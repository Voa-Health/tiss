"""Leitura de demonstrativos e conciliação de guias."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any, Literal, NamedTuple

from lxml import etree

from ._schema import parser
from ._xml import local_name


class Decision:
    """Valores de decisão retornados pelo parser."""

    PAGO = "pago"
    GLOSADO = "glosado"
    GLOSA_PARCIAL = "glosa_parcial"


class RetornoError(ValueError):
    """Erro em um demonstrativo ou na conciliação de guias."""


class Decisao(NamedTuple):
    """Decisão interpretada para uma guia."""

    guia_ref: str
    decision: str
    motivo: str
    guia_operadora: str = ""
    tuss_code: str = ""
    valor_glosa_cents: int = 0
    valor_liberado_cents: int = 0

    def to_dict(self) -> dict[str, Any]:
        return self._asdict()


@dataclass(frozen=True)
class Proposta:
    """Ação proposta para uma guia identificada."""

    guia: Any
    acao: Literal["pagar", "glosar"]
    motivo: str
    decisoes: list[Decisao]


@dataclass(frozen=True)
class Reconciliacao:
    """Resultado do planejamento de conciliação."""

    propostas: list[Proposta]
    sem_par: list[Decisao]
    ambiguas: list[Decisao]


class _Item(NamedTuple):
    tuss_code: str
    valor_glosa_cents: int
    valor_liberado_cents: int
    motivo: str
    glosado: bool


def _child_text(elem: etree._Element, *names: str) -> str:
    wanted = set(names)
    for node in elem.iter():
        if local_name(node.tag) in wanted:
            return (node.text or "").strip()
    return ""


def _money_cents(text: str) -> int:
    value = (text or "").strip()
    if not re.fullmatch(
        r"(?:\d+(?:\.\d{1,2})?|(?:\d+|\d{1,3}(?:\.\d{3})+),\d{1,2})",
        value,
    ):
        raise RetornoError(f"Valor monetário ausente ou inválido: {text!r}")
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    with localcontext() as context:
        context.prec = max(28, len(value) + 2)
        return int(Decimal(value) * 100)


def _amount(elem: etree._Element, field: str) -> int:
    try:
        return _money_cents(_child_text(elem, field))
    except RetornoError as exc:
        raise RetornoError(f"{field}: {exc}") from exc


def _motivo(codigo: str, descricao: str) -> str:
    codigo, descricao = codigo.strip(), descricao.strip()
    if codigo and descricao:
        return f"{codigo} - {descricao}"
    return descricao or codigo


def _parse_item(proc: etree._Element) -> _Item:
    tuss = _child_text(proc, "codigoProcedimento")
    if not tuss:
        raise RetornoError("procedimento sem codigoProcedimento; codigoTabela não é código TUSS")
    glosa = _amount(proc, "valorGlosa")
    liberado = _amount(proc, "valorLiberado")
    codigo_glosa = _child_text(proc, "codigoGlosa")
    descricao_glosa = _child_text(proc, "descricaoGlosa", "motivoGlosa")
    glosado = glosa > 0 or bool(codigo_glosa)
    return _Item(
        tuss_code=tuss,
        valor_glosa_cents=glosa,
        valor_liberado_cents=liberado,
        motivo=_motivo(codigo_glosa, descricao_glosa),
        glosado=glosado,
    )


def _parse_official_item(detail: etree._Element, guide_motives: list[str]) -> _Item:
    procedure = next(
        (node for node in detail if local_name(node.tag) == "procedimento"),
        detail,
    )
    glosas = [node for node in detail if local_name(node.tag) == "relacaoGlosa"]
    glosa = sum(_amount(node, "valorGlosa") for node in glosas)
    liberado = _amount(detail, "valorLiberado")
    motives = [_motivo(_child_text(node, "tipoGlosa"), "") for node in glosas]
    motives.extend(guide_motives)
    return _Item(
        tuss_code=_child_text(procedure, "codigoProcedimento"),
        valor_glosa_cents=glosa,
        valor_liberado_cents=liberado,
        motivo="; ".join(dict.fromkeys(motivo for motivo in motives if motivo)),
        glosado=glosa > 0 or any(motives),
    )


def _guia_records(root: etree._Element) -> list[etree._Element]:
    parent_of = {child: parent for parent in root.iter() for child in parent}
    records: list[etree._Element] = []
    seen: set[int] = set()
    for node in root.iter():
        if local_name(node.tag) in {"numeroGuiaPrestador", "numeroGuiaOperadora"}:
            record = parent_of.get(node, root)
            if id(record) not in seen:
                seen.add(id(record))
                records.append(record)
    return records


def _decide_guia(record: etree._Element) -> list[Decisao]:
    guia_prestador = _child_text(record, "numeroGuiaPrestador")
    guia_operadora = _child_text(record, "numeroGuiaOperadora")
    if not guia_prestador and not guia_operadora:
        raise RetornoError("Guia sem identificador preenchido")
    details = [node for node in record if local_name(node.tag) == "detalhesGuia"]
    if details:
        guide_motives = [
            _motivo(_child_text(node, "codigoGlosa"), _child_text(node, "descricaoGlosa"))
            for node in record
            if local_name(node.tag) == "motivoGlosaGuia"
        ]
        items = [_parse_official_item(detail, guide_motives) for detail in details]
    else:
        items = [
            _parse_item(proc) for proc in record.iter() if local_name(proc.tag) == "procedimento"
        ]
    glosados = [item for item in items if item.glosado]

    def make(decision: str, reason: str, tuss: str, glosa: int, liberado: int) -> Decisao:
        return Decisao(
            guia_ref=guia_prestador,
            decision=decision,
            motivo=reason,
            guia_operadora=guia_operadora,
            tuss_code=tuss,
            valor_glosa_cents=glosa,
            valor_liberado_cents=liberado,
        )

    if items:
        if not glosados:
            return [
                make(
                    Decision.PAGO,
                    "",
                    "",
                    0,
                    sum(item.valor_liberado_cents for item in items),
                )
            ]
        if len(glosados) == len(items) and not any(item.valor_liberado_cents for item in items):
            reasons = list(dict.fromkeys(item.motivo for item in glosados if item.motivo))
            return [
                make(
                    Decision.GLOSADO,
                    "; ".join(reasons),
                    "",
                    sum(item.valor_glosa_cents for item in items),
                    0,
                )
            ]
        return [
            make(
                Decision.GLOSA_PARCIAL,
                item.motivo,
                item.tuss_code,
                item.valor_glosa_cents,
                item.valor_liberado_cents,
            )
            for item in glosados
        ]

    glosa_field = "valorGlosaGuia" if details else "valorGlosa"
    liberado_field = "valorLiberadoGuia" if details else "valorLiberado"
    glosa = _amount(record, glosa_field)
    liberado = _amount(record, liberado_field)
    code = _child_text(record, "codigoGlosa")
    description = _child_text(record, "descricaoGlosa", "motivoGlosa")
    if glosa > 0 or code:
        decision = Decision.GLOSA_PARCIAL if liberado else Decision.GLOSADO
        return [make(decision, _motivo(code, description), "", glosa, liberado)]
    return [make(Decision.PAGO, "", "", 0, liberado)]


def parse_demonstrativo(xml: str | bytes) -> list[Decisao]:
    """Interpreta o XML do demonstrativo em decisões por guia."""
    raw = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = etree.fromstring(raw, parser())
    except (etree.XMLSyntaxError, TypeError, ValueError) as exc:
        raise RetornoError(f"XML do demonstrativo malformado: {exc}") from exc
    decisions: list[Decisao] = []
    for record in _guia_records(root):
        decisions.extend(_decide_guia(record))
    if not decisions:
        raise RetornoError("Retorno sem guias identificadas; nenhuma baixa foi proposta")
    return decisions


def _get(obj: Any, key: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)


def plan_reconciliation(
    decisoes: list[Decisao],
    guias: list[Any],
    *,
    id_key: str = "id",
    prestador_key: str = "numero_guia_prestador",
    operadora_key: str = "numero_guia_operadora",
    status_key: str = "status",
) -> Reconciliacao:
    """Planeja propostas sem alterar os objetos de guia."""
    by_number: dict[str, dict[Any, Any]] = {}
    for guia in guias:
        identifier = _get(guia, id_key)
        if not identifier:
            raise RetornoError(f"Guia sem identificador {id_key!r}")
        for key in (prestador_key, operadora_key):
            number = _get(guia, key)
            if number:
                by_number.setdefault(str(number), {})[identifier] = guia

    grouped: dict[Any, tuple[Any, list[Decisao]]] = {}
    sem_par: list[Decisao] = []
    ambiguas: list[Decisao] = []
    for decision in dict.fromkeys(decisoes):
        if decision.decision not in {
            Decision.PAGO,
            Decision.GLOSADO,
            Decision.GLOSA_PARCIAL,
        }:
            raise RetornoError(f"Decisão desconhecida: {decision.decision}")
        matches: dict[Any, Any] = {}
        for number in (decision.guia_ref, decision.guia_operadora):
            if number:
                matches.update(by_number.get(str(number), {}))
        if not matches:
            sem_par.append(decision)
        elif len(matches) != 1:
            ambiguas.append(decision)
        else:
            identifier, guia = next(iter(matches.items()))
            grouped.setdefault(identifier, (guia, []))[1].append(decision)

    proposals: list[Proposta] = []
    for guia, rows in grouped.values():
        actions = {"pagar" if row.decision == Decision.PAGO else "glosar" for row in rows}
        if len(actions) != 1:
            ambiguas.extend(rows)
            continue
        action: Literal["pagar", "glosar"] = "pagar" if next(iter(actions)) == "pagar" else "glosar"
        target = "pago" if action == "pagar" else "glosado"
        if _get(guia, status_key) == target:
            continue
        reason = "; ".join(dict.fromkeys(row.motivo for row in rows if row.motivo))
        proposals.append(Proposta(guia, action, reason, rows))
    return Reconciliacao(proposals, sem_par, ambiguas)
