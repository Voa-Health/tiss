"""Montagem das partes tabulares de documentos SP/SADT."""

from __future__ import annotations

from typing import Any

from ._sadt_values import _clean, _domain_for, _fmt_decimal_display, _resolve_enum


def _build_solicitados(values: dict[str, Any]) -> list[dict[str, str]]:
    rows = values.get("procedimentos_solicitados") or []
    out: list[dict[str, str]] = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "sequencial": str(row.get("sequencial") or i),
                "tabela": _clean(row.get("tabela")),
                "codigo": _clean(row.get("codigo")),
                "descricao": _clean(row.get("descricao")),
                "quantidade_solicitada": _fmt_decimal_display(row.get("quantidade_solicitada")),
            }
        )
    return out


def _build_equipe(row: dict[str, Any], catalog: dict[str, Any]) -> list[dict[str, str]]:
    equipe = row.get("equipe") or []
    cols = {
        c["key"]: c
        for c in catalog["matrices"]["procedimentos_executados"].get(
            "profissional_executante_columns", []
        )
    }
    out: list[dict[str, str]] = []
    for p in equipe:
        if not isinstance(p, dict):
            continue
        entry: dict[str, str] = {}
        for key, spec in cols.items():
            val = p.get(key)
            if spec.get("type") == "enum":
                domain = _domain_for(spec, catalog)
                entry[key] = _resolve_enum(f"equipe.{key}", val, domain) if domain else _clean(val)
            else:
                entry[key] = _clean(val)
        out.append(entry)
    return out
