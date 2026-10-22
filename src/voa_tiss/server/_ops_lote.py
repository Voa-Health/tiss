from __future__ import annotations

from typing import Any

import voa_tiss

from ._ops_schemas import _LOTE_OBJECT_SCHEMA, Op, _object, _string

_AUDIT_CONTEXT_SCHEMA = {
    key: value
    for key, value in voa_tiss.json_schema("audit_context").items()
    if key not in {"$schema", "title"}
}
_REPORT = voa_tiss.json_schema("report")
_REJECTION_MAP_OUTPUT = {
    key: value
    for key, value in voa_tiss.json_schema("rejection_map").items()
    if key not in {"$schema", "title"}
}
_OBJECT_INPUT = _object({}, additional=True)
_BUILD_INPUT = _object(
    {"lote": _LOTE_OBJECT_SCHEMA},
    ["lote"],
    additional=True,
)
_BUILD_OUTPUT = _object({"xml": _string(), "hash": _string()}, ["xml", "hash"])
_HASH_OUTPUT = _object({"hash": _string()}, ["hash"])
_REPORT_INPUT = _object(
    {
        "findings": {
            "type": "array",
            "items": _object({}, additional=True),
        }
    },
    ["findings"],
    additional=True,
)


def _build(value: dict[str, Any]) -> dict[str, Any]:
    xml = voa_tiss.build_lote(value["lote"])
    return {"xml": xml.decode("ISO-8859-1"), "hash": voa_tiss.hash_epilogo(xml)}


def _hash(value: dict[str, Any]) -> dict[str, Any]:
    return {"hash": voa_tiss.hash_epilogo(value["xml"])}


def _audit(value: dict[str, Any]) -> dict[str, Any]:
    return voa_tiss.audit(
        value["lote"],
        contexto=value.get("contexto"),
        at=value.get("data"),
        operadora=value.get("operadora"),
    ).to_dict()


def _rejection_map(value: dict[str, Any]) -> dict[str, Any]:
    if "operadora" in value and "regras" in value:
        raise ValueError("Informe no máximo um dos campos 'operadora' ou 'regras'.")
    return voa_tiss.rejection_map(
        value["lotes"],
        contexto=value.get("contexto"),
        operadora=value.get("regras", value.get("operadora")),
        segredo_pseudonimo=value.get("segredo_pseudonimo"),
        at=value.get("data"),
    )


def _apply_fixes(value: dict[str, Any]) -> dict[str, Any]:
    return {"lote": voa_tiss.apply_fixes(value["lote"], value["report"])}


LOTE_OPS = (
    Op(
        "build",
        _build,
        _BUILD_INPUT,
        _BUILD_OUTPUT,
        (
            "Gera o XML TISS 4.03.00 de um lote em JSON, com hash do epílogo. "
            "Consulte tiss://schemas/lote para o esquema estrutural. "
            "Quando usar: depois de validar o lote em JSON sem erros. "
            "Quando não usar: para corrigir achados; use tiss_apply_fixes."
        ),
        3000,
        scope="tiss:build",
    ),
    Op(
        "hash",
        _hash,
        _object({"xml": _string()}, ["xml"]),
        _HASH_OUTPUT,
        (
            "Calcula o hash do epílogo de um XML TISS. "
            "Quando usar: para conferir a integridade do XML. "
            "Quando não usar: para validar o conteúdo; use tiss_validate."
        ),
        1000,
        scope="tiss:validate",
    ),
    Op(
        "audit",
        _audit,
        _object(
            {
                "lote": _OBJECT_INPUT,
                "contexto": _AUDIT_CONTEXT_SCHEMA,
                "data": {"type": "string", "format": "date"},
                "operadora": {
                    "type": ["string", "object"],
                    "pattern": "^[0-9]{5,6}$",
                },
            },
            ["lote"],
        ),
        _REPORT,
        (
            "Audita um lote JSON com regras locais e contexto da operadora. "
            "Quando usar: para identificar inconsistências administrativas. "
            "Quando não usar: para aplicar correções; use tiss_apply_fixes."
        ),
        1000,
        scope="tiss:rules",
    ),
    Op(
        "rejection_map",
        _rejection_map,
        _object(
            {
                "lotes": {
                    "type": "array",
                    "items": {"type": ["string", "object"]},
                    "minItems": 1,
                    "maxItems": 100,
                },
                "contexto": _AUDIT_CONTEXT_SCHEMA,
                "operadora": {"type": "string", "pattern": "^[0-9]{5,6}$"},
                "regras": _object({}, additional=True),
                "segredo_pseudonimo": {"type": "string", "minLength": 16},
                "data": {"type": "string", "format": "date"},
            },
            ["lotes"],
        ),
        _REJECTION_MAP_OUTPUT,
        (
            "Agrega achados por prestador e mês, sem expor dados das guias; "
            "CPF é pseudonimizado. Quando usar: para analisar rejeições por prestador. "
            "Quando não usar: para consultar guias individuais ou corrigir lotes."
        ),
        4000,
        path="/v1/rejection-map",
        scope="tiss:rules",
    ),
    Op(
        "apply_fixes",
        _apply_fixes,
        _object(
            {"lote": _OBJECT_INPUT, "report": _REPORT_INPUT},
            ["lote", "report"],
        ),
        _object({"lote": _OBJECT_INPUT}, ["lote"]),
        (
            "Aplica correções JSON Patch de um relatório ao lote. "
            "Quando usar: depois de tiss_validate ou tiss_audit com achados corrigíveis. "
            "Quando não usar: para inventar dados ausentes; peça-os ao usuário."
        ),
        1500,
        scope="tiss:build",
    ),
)


__all__ = ["LOTE_OPS"]
