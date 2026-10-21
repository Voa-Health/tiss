"""Primitivas reutilizáveis para regras de auditoria."""

from __future__ import annotations

import datetime
from typing import Any

AUDIT_RULES = {
    "lote.vazio": "empty",
    "lote.acima_do_teto": "greater",
    "audit.tabela_sem_procedimentos": "empty",
    "audit.operadora_divergente": "different_if_both",
    "audit.tabela_fora_de_vigencia": "outside_window",
    "audit.procedimento_ausente": "empty",
    "tuss.inexistente": "empty",
    "tuss.fora_de_vigencia": "no_valid_record",
    "audit.procedimento_fora_da_tabela": "not_in",
    "autorizacao_requerida": "in",
    "audit.autorizacao_ausente": "empty",
    "audit.autorizacao_vencida": "expired",
    "audit.valor_nao_positivo": "nonpositive",
    "audit.carteirinha_ausente": "empty",
    "audit.carteirinha_inativa": "inactive",
    "audit.carteirinha_vencida": "expired",
    "audit.data_ausente": "missing",
}


def _day(value: Any) -> datetime.date | None:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _money(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _matches(rule: str, value: Any, expected: Any = None) -> bool:
    match AUDIT_RULES[rule]:
        case "empty":
            return not value
        case "greater":
            return bool(value > expected)
        case "different_if_both":
            left, right = value
            return bool(left and right and left != right)
        case "outside_window":
            reference, start, end = value
            return reference is not None and (
                (start is not None and reference < start) or (end is not None and reference >= end)
            )
        case "no_valid_record":
            records, reference = value
            return reference is not None and not any(
                (not row.get("vigencia_inicio") or reference.isoformat() >= row["vigencia_inicio"])
                and (not row.get("vigencia_fim") or reference.isoformat() < row["vigencia_fim"])
                for row in records
            )
        case "not_in":
            return value not in expected
        case "in":
            return value in expected
        case "expired":
            expiry, reference = value
            return expiry is not None and reference is not None and reference >= expiry
        case "nonpositive":
            return value is not None and value <= 0
        case "inactive":
            return value is False
        case "missing":
            return value is None
        case _:
            raise ValueError(f"Regra de auditoria desconhecida: {rule}")
