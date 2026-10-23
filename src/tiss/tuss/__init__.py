"""Consultas locais ao conjunto de dados TUSS."""

from __future__ import annotations

import copy
import datetime
from typing import Any

from ._index import get_default_index


def _check_table(tabela: str | None) -> None:
    tables = get_default_index().metadata.get("tables", {})
    if tabela is not None and str(tabela) not in tables:
        valid = ", ".join(sorted(tables))
        raise ValueError(f"Tabela desconhecida {tabela!r}; tabelas disponíveis: {valid}")


def lookup(
    code: str,
    *,
    tabela: str | None = None,
    include_expired: bool = True,
    today: datetime.date | None = None,
) -> list[dict[str, Any]]:
    """Busca correspondências exatas de código."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code não pode ser vazio")
    _check_table(tabela)
    return copy.deepcopy(
        get_default_index().get(
            code.strip(), tabela=tabela, include_expired=include_expired, today=today
        )
    )


def search(
    text: str,
    tabela: str | None = None,
    *,
    include_expired: bool = False,
    today: datetime.date | None = None,
) -> list[dict[str, Any]]:
    """Busca por código, termo, descrição e tokens."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text não pode ser vazio")
    _check_table(tabela)
    return copy.deepcopy(
        get_default_index().lookup(
            text.strip(), tabela=tabela, include_expired=include_expired, today=today
        )
    )


def tables() -> list[dict[str, Any]]:
    """Lista as tabelas disponíveis e seus totais."""
    return copy.deepcopy(get_default_index().tables())


def info() -> dict[str, Any]:
    """Retorna a fonte, licença, quantidade e metadados dos dados."""
    index = get_default_index()
    metadata = index.metadata
    return {
        "source": metadata.get("source"),
        "license": metadata.get("license"),
        "records": index.size,
        "tables": copy.deepcopy(metadata.get("tables", {})),
    }


__all__ = ["info", "lookup", "search", "tables"]
