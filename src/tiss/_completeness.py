"""Verifica campos obrigatórios da guia SP/SADT."""

from __future__ import annotations

from typing import Any

from ._text import is_present, normalise_text


def _is_truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "nao", "não", "off", "no", "n")
    return bool(value)


def _code_of(value: Any) -> str:
    """Extrai o código inicial de um valor de domínio."""
    s = "" if value is None else str(value).strip()
    return s.split(" - ", 1)[0].strip() if " - " in s else s


def _condition_met(when: dict[str, Any], values: dict[str, Any]) -> bool:
    field = when.get("field")
    if field is None:
        return False
    value = values.get(field)
    if "equals" in when:
        eq = str(when["equals"]).strip()
        return _code_of(value) == eq or normalise_text(value) == normalise_text(eq)
    if when.get("truthy"):
        return _is_truthy(value)
    return False


def _has_any_procedimento(values: dict[str, Any], matrices: list[str]) -> bool:
    for name in matrices:
        rows = values.get(name) or []
        if isinstance(rows, (list, tuple)) and any(
            isinstance(r, dict) and is_present(r.get("codigo")) for r in rows
        ):
            return True
    return False


def missing_mandatory(values: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    """Retorna os campos obrigatórios ainda ausentes."""
    fields: dict[str, dict[str, Any]] = catalog.get("fields", {})
    missing: set[str] = set()

    for name, spec in fields.items():
        if spec.get("obrigatoriedade") == "obrigatorio" and not is_present(values.get(name)):
            missing.add(name)

    for rule in catalog.get("conditional_rules", []):
        if _condition_met(rule.get("when", {}), values):
            for req in rule.get("require", []):
                if not is_present(values.get(req)):
                    missing.add(req)

    for rule in catalog.get("row_conditional_rules", []):
        matrix_name = rule.get("matrix")
        rows = values.get(matrix_name) or []
        when = rule.get("when", {})
        field = when.get("field")
        for i, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            fired = (
                _is_truthy(row.get(field))
                if when.get("truthy")
                else _code_of(row.get(field)) == str(when.get("equals", "")).strip()
            )
            if fired:
                for req in rule.get("require", []):
                    if not is_present(row.get(req)):
                        missing.add(f"{matrix_name}[{i}].{req}")

    for rule in catalog.get("structural_rules", []):
        if rule.get("rule") == "at_least_one_procedimento" and not _has_any_procedimento(
            values, rule.get("matrices", [])
        ):
            missing.add(rule.get("key", "procedimentos"))

    return sorted(missing)
