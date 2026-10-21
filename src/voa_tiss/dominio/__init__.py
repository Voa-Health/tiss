"""Consulta offline dos domínios TISS publicados pela ANS."""

from __future__ import annotations

import datetime
import json
import unicodedata
from copy import deepcopy
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast

from .._glosa import _glosas, glosa


@lru_cache(maxsize=1)
def _data() -> dict[str, Any]:
    path = files(__package__) / "_data" / "domain.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _fold(text: str) -> str:
    raw = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(raw.casefold().split())


def _current(row: dict[str, Any], at: datetime.date | str | None) -> bool:
    if at is None:
        return True
    date = at.isoformat() if isinstance(at, datetime.date) else str(at)
    start = row.get("vigencia_inicio") or ""
    end = row.get("vigencia_fim") or ""
    return (not start or date >= start) and (not end or date <= end)


def lookup(
    tabela: str,
    codigo: str,
    *,
    include_expired: bool = True,
    at: datetime.date | str | None = None,
) -> list[dict[str, Any]]:
    """Busque registros de domínio pelo código."""
    if not tabela or not codigo:
        raise ValueError("tabela e codigo não podem ser vazios")
    if str(tabela) == "38":
        record = glosa(str(codigo))
        if record is None:
            return []
        return [
            {
                "tabela": "38",
                "codigo": record["codigo"],
                "termo": record["descricao"],
                "descricao": record["descricao"],
                "grupo": record["grupo"],
                "vigencia_inicio": "",
                "vigencia_fim": "",
            }
        ]
    tables = _data()["tables"]
    key = str(tabela)
    if key not in tables:
        raise ValueError(f"Tabela desconhecida: {tabela}")
    rows = [
        row
        for row in _data()["records"]
        if row["tabela"] == key
        and row["codigo"] == str(codigo)
        and (include_expired or _current(row, at))
    ]
    return deepcopy(rows)


def search(
    text: str,
    tabela: str | None = None,
    *,
    include_expired: bool = False,
    at: datetime.date | str | None = None,
) -> list[dict[str, Any]]:
    """Busque registros de domínio por texto."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text não pode ser vazio")
    query = _fold(text)
    if tabela in {None, "38"}:
        glosa_rows = [
            {
                "tabela": "38",
                "codigo": row["codigo"],
                "termo": row["descricao"],
                "descricao": row["descricao"],
                "grupo": row["grupo"],
                "vigencia_inicio": "",
                "vigencia_fim": "",
            }
            for row in _glosas()["records"]
            if query in _fold(row["descricao"])
        ]
        if tabela == "38":
            return deepcopy(glosa_rows)
    else:
        glosa_rows = []
    if tabela is not None and str(tabela) not in _data()["tables"]:
        raise ValueError(f"Tabela desconhecida: {tabela}")
    matches = []
    for row in _data()["records"]:
        if tabela is not None and row["tabela"] != str(tabela):
            continue
        if not include_expired and not _current(row, at):
            continue
        if query in _fold(" ".join((row.get("termo", ""), row.get("descricao", "")))):
            matches.append(row)
    return deepcopy(glosa_rows + matches)


def tables() -> list[dict[str, Any]]:
    """Liste as tabelas locais disponíveis."""
    result = [
        {"tabela": table, "nome": name, "registros": count}
        for table, name, count in _data()["table_info"]
    ]
    result.append(
        {
            "tabela": "38",
            "nome": "Terminologia de mensagens (glosas, negativas e outras)",
            "registros": len(_glosas()["records"]),
        }
    )
    return result


def info() -> dict[str, Any]:
    """Retorne a origem e a licença dos dados locais."""
    data = _data()

    return {
        key: deepcopy(data.get(key)) for key in ("source", "license", "tables", "records_count")
    } | {
        "tabela38_source": _glosas()["source"],
        "tabela38_license": _glosas()["license"],
        "tabela38_records": len(_glosas()["records"]),
    }


__all__ = ["info", "lookup", "search", "tables"]
