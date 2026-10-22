"""Estruturas de validação e esquemas JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from ._audit_schema import audit_context_schema
from ._lote_codec import json_schema as lote_json_schema
from ._mapa_schema import rejection_map_schema
from ._rules_schema import rules_schema
from .codes import CODES


@dataclass(frozen=True)
class Finding:
    """Achado produzido pela validação."""

    code: str
    severity: Literal["error", "warning"]
    guia: str | None
    xpath: str | None
    pointer: str | None
    message: str
    fix: list[dict[str, Any]] | None
    needs: list[str] | None
    glosa: str | None = None
    rule: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "guia": self.guia,
            "xpath": self.xpath,
            "pointer": self.pointer,
            "message": self.message,
            "fix": self.fix,
            "needs": self.needs,
            "glosa": self.glosa,
            "rule": self.rule,
        }


@dataclass(frozen=True)
class Report:
    """Resultado da validação de um lote."""

    valid: bool
    version: str | None
    findings: tuple[Finding, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "version": self.version,
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def json_schema(
    kind: Literal["finding", "report", "lote", "audit_context", "rules", "rejection_map"],
) -> dict[str, Any]:
    """Retorna o esquema JSON de um tipo suportado."""

    def nullable(type_name: str) -> dict[str, Any]:
        return {"type": [type_name, "null"]}

    if kind == "finding":
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Finding",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "code",
                "severity",
                "guia",
                "xpath",
                "pointer",
                "message",
                "fix",
                "needs",
                "glosa",
                "rule",
            ],
            "properties": {
                "code": {"enum": sorted(CODES)},
                "severity": {"enum": ["error", "warning"]},
                "guia": nullable("string"),
                "xpath": nullable("string"),
                "pointer": nullable("string"),
                "message": {"type": "string"},
                "fix": {
                    "anyOf": [
                        {"type": "null"},
                        {"type": "array", "items": {"type": "object"}},
                    ]
                },
                "needs": {
                    "anyOf": [
                        {"type": "null"},
                        {"type": "array", "items": {"type": "string"}},
                    ]
                },
                "glosa": nullable("string"),
                "rule": nullable("object"),
            },
        }
    if kind == "report":
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Report",
            "type": "object",
            "additionalProperties": False,
            "required": ["valid", "version", "findings"],
            "properties": {
                "valid": {"type": "boolean"},
                "version": nullable("string"),
                "findings": {
                    "type": "array",
                    "items": json_schema("finding"),
                },
            },
        }
    if kind in {"lote", "audit_context", "rules"}:
        if kind == "lote":
            return lote_json_schema()
        if kind == "audit_context":
            return audit_context_schema()
        return rules_schema()
    if kind == "rejection_map":
        return rejection_map_schema()
    raise ValueError(
        "kind deve ser 'finding', 'report', 'lote', 'audit_context', 'rules' ou 'rejection_map'"
    )
