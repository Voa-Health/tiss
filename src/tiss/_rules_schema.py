"""Esquema JSON do pacote declarativo de regras de operadora."""

from typing import Any


def rules_schema() -> dict[str, Any]:
    """Retorna o esquema JSON de um pacote de regras."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Pacote declarativo de regras de operadora",
        "type": "object",
        "additionalProperties": False,
        "required": ["operadora", "mantenedor", "official", "versao_tiss", "regras"],
        "properties": {
            "operadora": {"type": "string"},
            "mantenedor": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tipo"],
                "properties": {
                    "tipo": {"enum": ["comunidade", "operadora"]},
                    "registro_ans": {"type": "string"},
                },
            },
            "official": {"type": "boolean"},
            "versao_tiss": {"const": "4.03.00"},
            "regras": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "descricao", "source", "severity", "check"],
                    "properties": {
                        "id": {"type": "string"},
                        "descricao": {"type": "string"},
                        "source": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["url", "titulo", "data", "acesso"],
                            "properties": {
                                "url": {"type": "string"},
                                "titulo": {"type": "string"},
                                "data": {"type": "string"},
                                "acesso": {"type": "string"},
                            },
                        },
                        "severity": {"enum": ["error", "warning"]},
                        "glosa": {"type": ["string", "null"]},
                        "tipo_guia": {"enum": ["consulta", "sp_sadt"]},
                        "check": {
                            "oneOf": [
                                _check_schema(tipo)
                                for tipo in (
                                    "obrigatorio",
                                    "padrao",
                                    "valores",
                                    "max_itens",
                                    "combinacao_proibida",
                                    "exige_autorizacao",
                                )
                            ]
                        },
                    },
                },
            },
        },
    }


def _check_schema(tipo: str) -> dict[str, Any]:
    base: dict[str, Any] = {"tipo": {"const": tipo}, "pointer": {"type": "string"}}
    if tipo == "padrao":
        base["regex"] = {"type": "string", "maxLength": 200}
    elif tipo == "valores":
        base["permitidos"] = {"type": "array"}
    elif tipo == "max_itens":
        base["max"] = {"type": "integer", "minimum": 0}
    elif tipo == "combinacao_proibida":
        base = {
            "tipo": {"const": tipo},
            "se": {"type": "object"},
            "entao_proibido": {"type": "object"},
        }
    elif tipo == "exige_autorizacao":
        base = {
            "tipo": {"const": tipo},
            "codigos": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
        }
    required = list(base)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": base,
    }
