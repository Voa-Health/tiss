from __future__ import annotations

from typing import Any

from voa_tiss import dominio, operadoras
from voa_tiss._glosa import glosa

from ._ops_schemas import Op, _array, _object, _string

_RECORD = _object({}, additional=True)
_RESULTS = _object({"resultados": _array(_RECORD)}, ["resultados"])
_DOMAIN_INPUT = {
    "type": "object",
    "properties": {
        "tabela": _string(),
        "codigo": _string(),
        "texto": _string(),
        "include_expired": {"type": "boolean"},
        "data": {"type": "string", "format": "date"},
        "limite": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
    },
    "additionalProperties": False,
    "dependentRequired": {"codigo": ["tabela"]},
    "not": {"required": ["codigo", "texto"]},
}
_GLOSA_SOURCE = _object(
    {"data": _string(), "titulo": _string(), "url": _string()},
    ["data", "titulo", "url"],
    additional=True,
)
_GLOSA_ORIENTACAO = _object(
    {"fonte": _string(), "texto": _string()},
    ["fonte", "texto"],
    additional=True,
)
_GLOSA_OUTPUT = _object(
    {
        "codigo": _string(),
        "descricao": _string(),
        "grupo": _string(),
        "fonte": _GLOSA_SOURCE,
        "orientacao": _GLOSA_ORIENTACAO,
    },
    ["codigo", "descricao", "grupo", "fonte", "orientacao"],
    additional=True,
)


def _explain_glosa(value: dict[str, Any]) -> dict[str, Any]:
    result = glosa(value["codigo"])
    if result is None:
        raise LookupError(f"Glosa não encontrada: {value['codigo']}")
    return result


def _domain(value: dict[str, Any]) -> dict[str, Any]:
    if "codigo" in value:
        return {
            "resultados": dominio.lookup(
                value["tabela"],
                value["codigo"],
                include_expired=value.get("include_expired", True),
                at=value.get("data"),
            )
        }
    if "texto" in value:
        return {
            "resultados": dominio.search(
                value["texto"],
                tabela=value.get("tabela"),
                include_expired=value.get("include_expired", False),
                at=value.get("data"),
            )[: value.get("limite", 20)]
        }
    return {"tabelas": dominio.tables()}


def _operator_lookup(value: dict[str, Any]) -> dict[str, Any]:
    return {"resultados": operadoras.search(value["texto"], limit=value.get("limite", 10))}


CONSULTA_OPS = (
    Op(
        "glosa_explain",
        _explain_glosa,
        _object(
            {"codigo": {"type": "string", "pattern": "^[0-9]{4}$"}},
            ["codigo"],
        ),
        _GLOSA_OUTPUT,
        (
            "Explica um código da Tabela 38 da ANS. "
            "Quando usar: ao interpretar uma glosa recebida. "
            "Quando não usar: para validar ou corrigir o lote."
        ),
        1000,
        method="GET",
        path="/v1/glosas/{codigo}",
    ),
    Op(
        "dominio",
        _domain,
        _DOMAIN_INPUT,
        _object(
            {
                "tabelas": _array(_RECORD),
                "resultados": _array(_RECORD),
            }
        ),
        (
            "Consulta tabelas e códigos de domínio TISS. "
            "Quando usar: para localizar um código ou termo de domínio. "
            "Quando não usar: para buscar procedimentos TUSS; use tuss_search."
        ),
        1000,
        method="GET",
        path="/v1/dominio",
    ),
    Op(
        "operadora_lookup",
        _operator_lookup,
        _object(
            {
                "texto": _string(),
                "limite": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
            },
            ["texto"],
        ),
        _RESULTS,
        (
            "Busca operadoras ativas pelo nome, registro, CNPJ ou localidade. "
            "Quando usar: para localizar uma operadora na base pública. "
            "Quando não usar: para consultar vínculos hospitalares; use tiss_rede."
        ),
        1000,
        method="GET",
        path="/v1/operadoras",
    ),
)


__all__ = ["CONSULTA_OPS"]
