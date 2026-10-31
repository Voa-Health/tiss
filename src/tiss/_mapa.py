"""Agregação privada de achados por prestador."""

from __future__ import annotations

import datetime
import hashlib
import hmac
import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, cast

from ._audit import AuditContext, audit
from ._check import check
from ._lote_codec import parse_lote
from ._report import Finding
from ._validate import validate

_POINTER_GUIDE = re.compile(r"^/guias/(\d+)")
_POINTER_ITEM = re.compile(r"^/guias/\d+/procedimentos_executados/(\d+)")
_XPATH_ITEM = re.compile(r"procedimentoExecutado\[(\d+)\]")
_XPATH_GUIDE = re.compile(r"(guiaSP-SADT|guiaConsulta)\[(\d+)\]")
_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")
_CENT = Decimal("0.01")

_GuideKey = tuple[int, int]
_Coverage = dict[_GuideKey, Literal[True] | set[int]]


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _money(value: Any) -> Decimal:
    if isinstance(value, bool):
        return Decimal("0.00")
    try:
        return (Decimal(str(value)) / 100).quantize(_CENT)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _guide_value(guide: dict[str, Any], items: list[Any]) -> Decimal:
    totals = _object(guide.get("valor_total"))
    if "valor_total_geral" in totals:
        return _money(totals["valor_total_geral"])
    if guide.get("tipo") == "consulta":
        procedure = _object(_object(guide.get("dados_atendimento")).get("procedimento"))
        if "valor_procedimento" in procedure:
            return _money(procedure["valor_procedimento"])
    return sum(
        (_money(_object(item).get("valor_total")) for item in items),
        Decimal("0.00"),
    ).quantize(_CENT)


def _service_month(guide: dict[str, Any], lote: dict[str, Any]) -> str | None:
    items = guide.get("procedimentos_executados", [])
    items = items if isinstance(items, list) else []
    raw_dates = [item.get("data_execucao") for item in items if isinstance(item, dict)]
    dates: list[str] = [
        value for value in raw_dates if isinstance(value, str) and _DATE_PREFIX.match(value)
    ]
    valid_dates: list[datetime.date] = []
    for value in dates:
        try:
            valid_dates.append(datetime.date.fromisoformat(value[:10]))
        except ValueError:
            continue
    if valid_dates:
        return min(valid_dates).strftime("%Y-%m")
    attended = _object(guide.get("dados_atendimento")).get("data_atendimento")
    transaction_date = _object(lote.get("transacao")).get("data_registro_transacao")
    for candidate_date in (attended, transaction_date):
        if isinstance(candidate_date, str) and _DATE_PREFIX.match(candidate_date):
            try:
                return datetime.date.fromisoformat(candidate_date[:10]).strftime("%Y-%m")
            except ValueError:
                continue
    return None


def _provider_id(prestador: Any, segredo_pseudonimo: str | bytes | None) -> str | None:
    values = _object(prestador)
    codigo = values.get("codigo_prestador_na_operadora")
    if codigo is not None and str(codigo).strip():
        return f"codigo:{str(codigo).strip()}"
    cnpj = re.sub(r"\D", "", str(values.get("cnpj", "")))
    if len(cnpj) == 14:
        return f"cnpj:{cnpj}"
    cpf = re.sub(r"\D", "", str(values.get("cpf", "")))
    if len(cpf) == 11:
        if segredo_pseudonimo is None:
            raise ValueError(
                "Informe segredo_pseudonimo para lotes com prestador identificado por CPF."
            )
        secret = (
            segredo_pseudonimo.encode("utf-8")
            if isinstance(segredo_pseudonimo, str)
            else segredo_pseudonimo
        )
        digest = hmac.new(secret, cpf.encode("ascii"), hashlib.sha256).hexdigest()
        return f"cpf:hmac:{digest}"
    return None


def _findings(
    raw: str | bytes,
    lote: dict[str, Any],
    *,
    contexto: AuditContext | None,
    operadora: Any,
    at: datetime.date | str | None,
) -> list[Finding]:
    checked = validate(raw, operadora=operadora).findings
    audited = audit(lote, contexto=contexto, at=at).findings
    unique: dict[tuple[str, str | None, str | None, str], Finding] = {}
    for finding in (*checked, *audited):
        key = (finding.code, finding.pointer, finding.xpath, finding.message)
        unique.setdefault(key, finding)
    return list(unique.values())


def _target_guides(finding: Finding, guides: list[Any]) -> tuple[list[int], int | None]:
    pointer_match = _POINTER_GUIDE.match(finding.pointer or "")
    item_match = _POINTER_ITEM.match(finding.pointer or "")
    item_index = int(item_match.group(1)) if item_match else None
    if pointer_match:
        index = int(pointer_match.group(1))
        if index < len(guides):
            return [index], item_index
    if finding.guia is not None:
        for index, value in enumerate(guides):
            guide = _object(value)
            header = _object(guide.get("cabecalho_guia"))
            consultation = _object(guide.get("cabecalho_consulta"))
            number = header.get("numero_guia_prestador") or consultation.get(
                "numero_guia_prestador"
            )
            if number is not None and str(number) == finding.guia:
                item_match = _XPATH_ITEM.search(finding.xpath or "")
                item_index = int(item_match.group(1)) - 1 if item_match else None
                return [index], item_index
    type_match = _XPATH_GUIDE.search(finding.xpath or "")
    if type_match:
        expected_type = "sp_sadt" if type_match.group(1) == "guiaSP-SADT" else "consulta"
        position = int(type_match.group(2))
        matching = [
            index
            for index, value in enumerate(guides)
            if _object(value).get("tipo") == expected_type
        ]
        if 0 < position <= len(matching):
            item_match = _XPATH_ITEM.search(finding.xpath or "")
            item_index = int(item_match.group(1)) - 1 if item_match else None
            return [matching[position - 1]], item_index
    return list(range(len(guides))), None


def _add_coverage(coverage: _Coverage, key: _GuideKey, item: int | None) -> None:
    current = coverage.get(key)
    if current is True:
        return
    if item is None:
        coverage[key] = True
    elif isinstance(current, set):
        current.add(item)
    else:
        coverage[key] = {item}


def _coverage_value(coverage: _Coverage, guides: dict[_GuideKey, dict[str, Any]]) -> Decimal:
    total = Decimal("0.00")
    for key, affected in coverage.items():
        guide = guides[key]
        if affected is True:
            total += guide["total"]
        else:
            total += sum(
                (guide["items"][index] for index in affected if 0 <= index < len(guide["items"])),
                Decimal("0.00"),
            )
    return total.quantize(_CENT)


def _money_text(value: Decimal) -> str:
    return format(value.quantize(_CENT), ".2f")


def rejection_map(
    lotes: Iterable[str | bytes | dict[str, Any]],
    *,
    contexto: AuditContext | None = None,
    operadora: Any = None,
    segredo_pseudonimo: str | bytes | None = None,
    at: datetime.date | str | None = None,
) -> dict[str, Any]:
    """Agrega achados por prestador sem expor dados de guias."""
    ignored: list[int] = []
    line_state: dict[tuple[str, str | None, str, str | None], dict[str, Any]] = {}
    summary: dict[tuple[str, str | None], dict[str, Any]] = {}
    guide_values: dict[_GuideKey, dict[str, Any]] = {}
    guide_count = 0
    lot_count = 0

    for lot_index, raw in enumerate(lotes):
        lot_count += 1
        if isinstance(raw, (str, bytes)):
            try:
                lote = cast(dict[str, Any], parse_lote(raw))
            except Exception:
                ignored.append(lot_index)
                continue
            findings = _findings(raw, lote, contexto=contexto, operadora=operadora, at=at)
        elif isinstance(raw, dict):
            lote = raw
            findings = list(check(lote, contexto=contexto, operadora=operadora, at=at).findings)
        else:
            ignored.append(lot_index)
            continue

        provider = _provider_id(lote.get("prestador"), segredo_pseudonimo)
        if provider is None:
            ignored.append(lot_index)
            continue
        raw_guides = lote.get("guias", [])
        guides = raw_guides if isinstance(raw_guides, list) else []
        month_for_empty = _service_month({}, lote)
        if not guides:
            summary.setdefault(
                (provider, month_for_empty),
                {"guides": set(), "all": Decimal("0.00"), "affected": {}},
            )
            if findings:
                for finding in findings:
                    key = (provider, month_for_empty, finding.code, _rule_id(finding))
                    line = line_state.setdefault(
                        key,
                        {"glosa": finding.glosa, "coverage": {}},
                    )
                    line["glosa"] = line["glosa"] or finding.glosa
            continue

        indexes: dict[int, _GuideKey] = {}
        for guide_index, raw_guide in enumerate(guides):
            guide = _object(raw_guide)
            items = guide.get("procedimentos_executados", [])
            items = items if isinstance(items, list) else []
            guide_key = (lot_index, guide_index)
            indexes[guide_index] = guide_key
            month = _service_month(guide, lote)
            item_values = [_money(_object(item).get("valor_total")) for item in items]
            value = _guide_value(guide, items)
            guide_values[guide_key] = {
                "provider": provider,
                "month": month,
                "total": value,
                "items": item_values,
            }
            group = summary.setdefault(
                (provider, month),
                {"guides": set(), "all": Decimal("0.00"), "affected": {}},
            )
            group["guides"].add(guide_key)
            group["all"] += value
            guide_count += 1

        for finding in findings:
            target_indexes, item_index = _target_guides(finding, guides)
            if not target_indexes:
                continue
            rule_id = _rule_id(finding)
            for guide_index in target_indexes:
                guide_key = indexes[guide_index]
                guide_info = guide_values[guide_key]
                month = guide_info["month"]
                line_key = (provider, month, finding.code, rule_id)
                line = line_state.setdefault(
                    line_key,
                    {"glosa": finding.glosa, "coverage": {}},
                )
                line["glosa"] = line["glosa"] or finding.glosa
                _add_coverage(line["coverage"], guide_key, item_index)
                group = summary[(provider, month)]
                _add_coverage(group["affected"], guide_key, item_index)

    lines: list[dict[str, Any]] = []
    for (provider, month, code, rule_id), state in sorted(
        line_state.items(),
        key=lambda entry: (
            entry[0][0],
            entry[0][1] or "",
            entry[0][2],
            entry[0][3] or "",
        ),
    ):
        coverage = state["coverage"]
        lines.append(
            {
                "provider": provider,
                "month": month,
                "code": code,
                "glosa": state["glosa"],
                "rule_id": rule_id,
                "guias": len(coverage),
                "affected_amount": _money_text(_coverage_value(coverage, guide_values)),
            }
        )

    prestadores = []
    for (provider, month), group in sorted(
        summary.items(), key=lambda entry: (entry[0][0], entry[0][1] or "")
    ):
        affected = group["affected"]
        prestadores.append(
            {
                "provider": provider,
                "month": month,
                "guias": len(group["guides"]),
                "guias_with_finding": len(affected),
                "total_amount": _money_text(group["all"]),
                "affected_amount": _money_text(_coverage_value(affected, guide_values)),
            }
        )
    return {
        "version": "2",
        "lotes": lot_count,
        "guias": guide_count,
        "ignored": ignored,
        "providers": prestadores,
        "rows": lines,
    }


def _rule_id(finding: Finding) -> str | None:
    return finding.rule.get("id") if finding.rule else None


__all__ = ["rejection_map"]
