"""Utilitários internos para XML."""

from __future__ import annotations

from typing import Any


def local_name(tag: Any) -> str:
    """Retorna o nome local de uma tag XML."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""
