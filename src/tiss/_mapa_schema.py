"""Esquema JSON do mapa de rejeição."""

from typing import Any


def rejection_map_schema() -> dict[str, Any]:
    """Retorna o esquema JSON do mapa de rejeição."""
    provider = {
        "type": "string",
        "pattern": r"^(codigo:.+|cnpj:\d{14}|cpf:hmac:[0-9a-f]{64})$",
    }
    month = {"type": ["string", "null"], "pattern": r"^\d{4}-\d{2}$"}
    money = {"type": "string", "pattern": r"^-?\d+\.\d{2}$"}
    line = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "provider",
            "month",
            "code",
            "glosa",
            "rule_id",
            "guias",
            "affected_amount",
        ],
        "properties": {
            "provider": provider,
            "month": month,
            "code": {"type": "string"},
            "glosa": {"type": ["string", "null"]},
            "rule_id": {"type": ["string", "null"]},
            "guias": {"type": "integer", "minimum": 0},
            "affected_amount": money,
        },
    }
    prestador = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "provider",
            "month",
            "guias",
            "guias_with_finding",
            "total_amount",
            "affected_amount",
        ],
        "properties": {
            "provider": provider,
            "month": month,
            "guias": {"type": "integer", "minimum": 0},
            "guias_with_finding": {"type": "integer", "minimum": 0},
            "total_amount": money,
            "affected_amount": money,
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Mapa de rejeição",
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "lotes", "guias", "ignored", "providers", "rows"],
        "properties": {
            "version": {"const": "2"},
            "lotes": {"type": "integer", "minimum": 0},
            "guias": {"type": "integer", "minimum": 0},
            "ignored": {"type": "array", "items": {"type": "integer", "minimum": 0}},
            "providers": {"type": "array", "items": prestador},
            "rows": {"type": "array", "items": line},
        },
    }
