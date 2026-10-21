"""Utilitários internos para texto."""

from __future__ import annotations

import unicodedata
from typing import Any


def normalise_text(value: Any) -> str:
    """Remove acentos e normaliza espaços e caixa."""
    text = "" if value is None else str(value)
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(stripped.split()).casefold()


def fold_ascii(value: str) -> str:
    """Remove caracteres não ASCII e normaliza espaços e caixa."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    return " ".join(decomposed.encode("ascii", "ignore").decode("ascii").lower().split())


def is_present(value: Any) -> bool:
    """Indica se o valor foi informado."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True
