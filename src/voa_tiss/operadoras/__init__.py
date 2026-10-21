"""Consulta offline das operadoras ativas cadastradas na ANS."""

from __future__ import annotations

import json
import unicodedata
from copy import deepcopy
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast


def _read(name: str) -> dict[str, Any]:
    path = files(__package__) / "_data" / name
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def _data() -> dict[str, Any]:
    return _read("operators.json")


@lru_cache(maxsize=1)
def _indicadores() -> dict[str, Any]:
    return _read("indicadores.json")


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(value.casefold().split())


def lookup(registro_ans: str) -> dict[str, Any] | None:
    """Busque uma operadora pelo registro ANS."""
    if not isinstance(registro_ans, str) or not registro_ans.strip():
        raise ValueError("registro_ans não pode ser vazio")
    code = registro_ans.strip()
    if not code.isdigit() or len(code) not in {5, 6}:
        return None
    record = _data()["records"].get(code.zfill(6))
    return deepcopy(record) if record else None


def search(text: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """Busque operadoras por nome, registro, CNPJ ou localidade."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text não pode ser vazio")
    if limit < 1:
        raise ValueError("limit deve ser positivo")
    query = _fold(text)
    rows = [
        record
        for record in _data()["records"].values()
        if query
        in _fold(
            " ".join(
                str(record.get(key) or "")
                for key in ("registro_ans", "razao_social", "nome_fantasia", "cnpj", "cidade", "uf")
            )
        )
    ]
    rows.sort(key=lambda record: (record.get("razao_social", ""), record["registro_ans"]))
    return deepcopy(rows[:limit])


def perfil(registro_ans: str) -> dict[str, Any] | None:
    """Junte o cadastro e os indicadores semestrais de glosa de uma operadora."""
    record = lookup(registro_ans)
    if record is None:
        return None
    painel = _indicadores()
    *chaves, _ = painel["colunas"]
    serie = [
        {
            **dict(zip(chaves, linha[:-1], strict=True)),
            "consistente": not linha[-1],
            "inconsistentes": list(linha[-1]),
        }
        for linha in painel["records"].get(record["registro_ans"], [])
    ]
    fonte = {key: painel["fonte"][key] for key in ("titulo", "url", "licenca", "atualizado_em")}
    return {**record, "indicadores": {"fonte": fonte, "serie": serie}}


def info() -> dict[str, Any]:
    """Retorne a origem e a quantidade de operadoras."""
    data = _data()
    return {
        "source": data.get("source"),
        "license": data.get("license"),
        "records": len(data["records"]),
    }


__all__ = ["info", "lookup", "perfil", "search"]
