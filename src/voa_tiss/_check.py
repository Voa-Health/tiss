"""Verificação e correção de lotes TISS em JSON."""

from __future__ import annotations

import datetime
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, cast

from ._audit import audit
from ._lote import Lote, LoteError
from ._lote_codec import build_lote
from ._lote_xml import _required_lote
from ._report import Finding, Report
from ._rules import rule_findings
from ._validate import _finding, validate
from .codes import CODE_CATALOG


def check(
    lote: dict[str, Any],
    *,
    contexto: Any = None,
    operadora: Any = None,
    at: Any = None,
) -> Report:
    """Aplica verificações estruturais, XML, auditoria e regras na ordem definida."""
    findings: list[Finding] = []
    try:
        _required_lote(lote)
    except (LoteError, TypeError, KeyError) as exc:
        findings.append(
            _finding(
                "lote.estrutura",
                f"Estrutura do lote inválida: {exc}.",
                needs=[
                    "/versao",
                    "/transacao",
                    "/prestador",
                    "/operadora",
                    "/numero_lote",
                    "/guias",
                ],
            )
        )
    try:
        xml = build_lote(cast(Lote, lote))
    except (LoteError, TypeError, ValueError, UnicodeEncodeError) as exc:
        code = (
            "lote.caractere_invalido"
            if isinstance(exc, UnicodeEncodeError) or "ISO-8859-1" in str(exc)
            else "lote.estrutura"
        )
        findings.append(
            _finding(
                code,
                "Lote contém caracteres incompatíveis com ISO-8859-1."
                if code == "lote.caractere_invalido"
                else f"Não foi possível gerar o XML do lote: {exc}.",
            )
        )
    else:
        checked = list(validate(xml, operadora=operadora).findings)
        fixes = {
            key: finding
            for key, finding in _deterministic_fixes(lote).items()
            if CODE_CATALOG[finding.code]["fix_kind"] == "json_patch"
        }
        fixed_codes = {finding.code for finding in fixes.values()}
        checked = [finding for finding in checked if finding.code not in fixed_codes]
        findings.extend(checked)
        findings.extend(fixes.values())
    try:
        findings.extend(audit(lote, contexto=contexto, at=at).findings)
    except (AttributeError, KeyError, TypeError, ValueError):
        findings.append(_finding("lote.estrutura", "Não foi possível auditar a estrutura do lote."))
    if operadora is not None:
        findings.extend(rule_findings(lote, operadora))
    deduplicated: dict[tuple[Any, ...], Finding] = {}
    for finding in findings:
        key = (finding.code, finding.pointer, finding.xpath, finding.message)
        deduplicated[key] = finding
    result = tuple(
        sorted(
            deduplicated.values(),
            key=lambda finding: (
                finding.pointer or "",
                finding.xpath or "",
                finding.code,
                finding.message,
            ),
        )
    )
    return Report(
        not any(finding.severity == "error" for finding in result),
        "4.03.00",
        result,
    )


def _test_replace(pointer: str, old: Any, new: Any) -> list[dict[str, Any]]:
    return [
        {"op": "test", "path": pointer, "value": old},
        {"op": "replace", "path": pointer, "value": new},
    ]


def _deterministic_fixes(lote: dict[str, Any]) -> dict[str, Finding]:
    result: dict[str, Finding] = {}
    for guide_index, guide in enumerate(lote.get("guias", [])):
        if not isinstance(guide, dict):
            continue
        items = guide.get("procedimentos_executados", [])
        if isinstance(items, list) and items:
            sequence_patch: list[dict[str, Any]] = []
            for index, item in enumerate(items, 1):
                if not isinstance(item, dict) or "sequencial_item" not in item:
                    continue
                if str(item["sequencial_item"]) != str(index):
                    sequence_path = (
                        f"/guias/{guide_index}/procedimentos_executados/{index - 1}/sequencial_item"
                    )
                    sequence_patch.extend(
                        _test_replace(
                            sequence_path,
                            item["sequencial_item"],
                            str(index),
                        )
                    )
            if sequence_patch:
                result[f"sequence:{guide_index}"] = Finding(
                    code="guia.sequencial",
                    severity="error",
                    guia=str(
                        guide.get("cabecalho_guia", {}).get("numero_guia_prestador") or guide_index
                    ),
                    xpath=None,
                    pointer=f"/guias/{guide_index}/procedimentos_executados",
                    message="Sequenciais dos itens devem ser contínuos a partir de 1.",
                    fix=sequence_patch,
                    needs=None,
                    glosa=CODE_CATALOG["guia.sequencial"]["glosa"],
                )
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                try:
                    unit = Decimal(int(item["valor_unitario"]))
                    quantity = Decimal(str(item["quantidade_executada"]))
                    factor = Decimal(str(item.get("reducao_acrescimo", "1")))
                    expected = int(
                        (unit * quantity * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                    )
                    current = int(item["valor_total"])
                except (KeyError, ValueError, TypeError, InvalidOperation):
                    continue
                if expected != current:
                    path = f"/guias/{guide_index}/procedimentos_executados/{index}/valor_total"
                    result[f"item:{guide_index}:{index}"] = Finding(
                        code="item.valor_divergente",
                        severity="error",
                        guia=str(
                            guide.get("cabecalho_guia", {}).get("numero_guia_prestador")
                            or guide_index
                        ),
                        xpath=None,
                        pointer=path,
                        message=(
                            "Valor total do item diverge da quantidade, valor unitário e fator."
                        ),
                        fix=_test_replace(path, current, expected),
                        needs=None,
                        glosa=CODE_CATALOG["item.valor_divergente"]["glosa"],
                    )
            value_total = guide.get("valor_total")
            if isinstance(value_total, dict) and "valor_total_geral" in value_total:
                try:
                    expected_total = sum(
                        int(
                            (
                                Decimal(int(item["valor_unitario"]))
                                * Decimal(str(item["quantidade_executada"]))
                                * Decimal(str(item.get("reducao_acrescimo", "1")))
                            ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                        )
                        for item in items
                        if isinstance(item, dict)
                    )
                    current_total = int(value_total["valor_total_geral"])
                except (KeyError, ValueError, TypeError):
                    expected_total = current_total = 0
                if expected_total != current_total:
                    path = f"/guias/{guide_index}/valor_total/valor_total_geral"
                    result[f"guide-total:{guide_index}"] = Finding(
                        code="lote.valor_total_geral",
                        severity="error",
                        guia=str(
                            guide.get("cabecalho_guia", {}).get("numero_guia_prestador")
                            or guide_index
                        ),
                        xpath=None,
                        pointer=path,
                        message="Total geral da guia diverge da soma dos itens.",
                        fix=_test_replace(path, current_total, expected_total),
                        needs=None,
                        glosa=CODE_CATALOG["lote.valor_total_geral"]["glosa"],
                    )
        for section_name in ("dados_atendimento", "dados_solicitacao"):
            section = guide.get(section_name)
            if not isinstance(section, dict):
                continue
            for date_key in ("data_atendimento", "data_solicitacao"):
                value = section.get(date_key)
                if not isinstance(value, str) or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
                    continue
                try:
                    normalized = f"{value[6:10]}-{value[3:5]}-{value[0:2]}"
                    datetime.date.fromisoformat(normalized)
                except ValueError:
                    continue
                path = f"/guias/{guide_index}/{section_name}/{date_key}"
                result[f"date:{guide_index}:{date_key}"] = Finding(
                    code="xsd.padrao",
                    severity="error",
                    guia=str(guide_index),
                    xpath=None,
                    pointer=path,
                    message="Data deve usar o formato ISO AAAA-MM-DD.",
                    fix=_test_replace(path, value, normalized),
                    needs=None,
                    glosa=CODE_CATALOG["xsd.padrao"]["glosa"],
                )
    provider = lote.get("prestador", {})
    for key, width in (("cnpj", 14), ("cpf", 11)):
        value = provider.get(key) if isinstance(provider, dict) else None
        if isinstance(value, str) and re.fullmatch(r"[\d./ -]+", value):
            normalized = re.sub(r"\D", "", value)
            if len(normalized) == width and normalized != value:
                path = f"/prestador/{key}"
                result[f"numeric:{key}"] = Finding(
                    code="xsd.padrao",
                    severity="error",
                    guia=None,
                    xpath=None,
                    pointer=path,
                    message=f"{key.upper()} deve conter somente {width} dígitos.",
                    fix=_test_replace(path, value, normalized),
                    needs=None,
                    glosa=CODE_CATALOG["xsd.padrao"]["glosa"],
                )
    return result


__all__ = ["check"]
