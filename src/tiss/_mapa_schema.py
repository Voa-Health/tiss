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
            "prestador",
            "mes",
            "codigo",
            "glosa",
            "rule_id",
            "guias",
            "valor_afetado",
        ],
        "properties": {
            "prestador": provider,
            "mes": month,
            "codigo": {"type": "string"},
            "glosa": {"type": ["string", "null"]},
            "rule_id": {"type": ["string", "null"]},
            "guias": {"type": "integer", "minimum": 0},
            "valor_afetado": money,
        },
    }
    prestador = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "prestador",
            "mes",
            "guias",
            "guias_com_achado",
            "valor_total",
            "valor_afetado",
        ],
        "properties": {
            "prestador": provider,
            "mes": month,
            "guias": {"type": "integer", "minimum": 0},
            "guias_com_achado": {"type": "integer", "minimum": 0},
            "valor_total": money,
            "valor_afetado": money,
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Mapa de rejeição",
        "type": "object",
        "additionalProperties": False,
        "required": ["versao", "lotes", "guias", "ignorados", "prestadores", "linhas"],
        "properties": {
            "versao": {"const": "1"},
            "lotes": {"type": "integer", "minimum": 0},
            "guias": {"type": "integer", "minimum": 0},
            "ignorados": {"type": "array", "items": {"type": "integer", "minimum": 0}},
            "prestadores": {"type": "array", "items": prestador},
            "linhas": {"type": "array", "items": line},
        },
    }
