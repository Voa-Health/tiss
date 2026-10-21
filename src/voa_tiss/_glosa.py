"""Consulta offline da terminologia de glosas da Tabela 38 da ANS."""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast


@lru_cache(maxsize=1)
def _glosas() -> dict[str, Any]:
    path = files("voa_tiss") / "_data" / "glosas.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def glosa(codigo: str) -> dict[str, Any] | None:
    if not isinstance(codigo, str) or not codigo.strip():
        raise ValueError("codigo não pode ser vazio")
    records = _glosas()["records"]
    low = 0
    high = len(records)
    while low < high:
        middle = (low + high) // 2
        candidate = records[middle]["codigo"]
        if candidate < codigo.strip():
            low = middle + 1
        else:
            high = middle
    if low < len(records) and records[low]["codigo"] == codigo.strip():
        return dict(deepcopy(records[low]))
    return None


__all__ = ["glosa"]
