"""Esquema JSON do contexto de auditoria."""

from typing import Any


def audit_context_schema() -> dict[str, Any]:
    """Retorna o esquema JSON do contexto de auditoria."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Contexto de auditoria TISS",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "tabela_operadora": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "registro_ans": {"type": "string"},
                    "procedimentos": {"type": "array", "items": {"type": "string"}},
                    "exige_autorizacao": {"type": "array", "items": {"type": "string"}},
                    "vigencia_inicio": {"type": "string", "format": "date"},
                    "vigencia_fim": {"type": ["string", "null"], "format": "date"},
                    "max_guias": {"type": "integer", "minimum": 1},
                },
            },
            "carteirinhas": {"type": "object"},
            "autorizacoes": {"type": "object"},
        },
    }
