"""Validação declarativa e segura de regras de operadora TISS."""

from __future__ import annotations

import json
import re
from importlib.resources import files
from typing import Any, TypedDict, cast

from ._report import Finding
from ._rules_schema import rules_schema


class RulePackage(TypedDict, total=False):
    operadora: str
    mantenedor: dict[str, Any]
    official: bool
    versao_tiss: str
    regras: list[dict[str, Any]]


def validate_package(package: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(package, dict):
        return ["Pacote de regras deve ser um objeto."]
    maintainer = package.get("mantenedor")
    if not isinstance(maintainer, dict) or maintainer.get("tipo") not in {
        "comunidade",
        "operadora",
    }:
        errors.append("mantenedor.tipo deve ser comunidade ou operadora.")
        kind = None
    else:
        kind = maintainer["tipo"]
    if package.get("official") is not (kind == "operadora"):
        errors.append("official deve ser true somente para mantenedor.tipo operadora.")
    rules = package.get("regras")
    if not isinstance(rules, list):
        errors.append("regras deve ser uma lista.")
        return errors
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict) or not isinstance(rule.get("check"), dict):
            errors.append(f"regras/{index}: regra ou check inválido.")
            continue
        check = rule["check"]
        if check.get("tipo") not in {
            "obrigatorio",
            "padrao",
            "valores",
            "max_itens",
            "combinacao_proibida",
        }:
            errors.append(f"regras/{index}: primitiva não suportada.")
            continue
        if check["tipo"] == "padrao":
            regex = check.get("regex")
            if not isinstance(regex, str) or len(regex) > 200:
                errors.append(f"regras/{index}: regex deve ter até 200 caracteres.")
            else:
                try:
                    re.compile(regex)
                except re.error:
                    errors.append(f"regras/{index}: regex inválida.")
    return errors


def _package(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        code = value.strip()
        if not code.isdigit() or len(code) not in {5, 6}:
            return None
        path = files("voa_tiss") / "rules" / f"{code.zfill(6)}.json"
        try:
            return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        except OSError:
            return None
    return value if isinstance(value, dict) and "regras" in value else None


def _resolve(document: Any, pointer: str) -> list[tuple[str, Any]]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return []
    current: list[tuple[str, Any]] = [("", document)]
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        next_values: list[tuple[str, Any]] = []
        for prefix, value in current:
            if token == "*" and isinstance(value, list):
                next_values.extend((f"{prefix}/{i}", child) for i, child in enumerate(value))
            elif isinstance(value, dict) and token in value:
                next_values.append((f"{prefix}/{token}", value[token]))
            elif isinstance(value, list) and token.isdigit() and int(token) < len(value):
                next_values.append((f"{prefix}/{token}", value[int(token)]))
        current = next_values
    return current


def _rule_finding(package: dict[str, Any], rule: dict[str, Any], pointer: str) -> Finding:
    source = dict(rule["source"])
    source["official"] = package["official"]
    return Finding(
        code=f"regra.{rule['check']['tipo']}",
        severity=rule["severity"],
        guia=None,
        xpath=None,
        pointer=pointer,
        message=rule["descricao"],
        fix=None,
        needs=[pointer],
        glosa=rule.get("glosa"),
        rule={
            "id": rule["id"],
            "source": source,
            "mantenedor": package["mantenedor"],
        },
    )


def rule_findings(lote: dict[str, Any], value: Any) -> list[Finding]:
    package = _package(value)
    if package is None:
        return []
    if validate_package(package):
        return [
            Finding(
                code="regra.padrao",
                severity="error",
                guia=None,
                xpath=None,
                pointer=None,
                message="Pacote de regras inválido.",
                fix=None,
                needs=["schemas/rules.schema.json"],
            )
        ]
    findings: list[Finding] = []
    for rule in package["regras"]:
        check = rule["check"]
        kind = check["tipo"]
        pointer = check.get("pointer", "")
        values = _resolve(lote, pointer) if pointer else []
        if kind == "obrigatorio":
            if not values:
                findings.append(_rule_finding(package, rule, pointer))
            continue
        if kind == "combinacao_proibida":
            condition = check["se"]
            targets = check["entao_proibido"]
            source = _resolve(lote, condition["pointer"])
            if any(value in condition.get("valores", []) for _, value in source):
                target = _resolve(lote, targets["pointer"])
                prohibited = targets.get("valores", [])
                failed = (not target and targets.get("ausente") is True) or any(
                    value in prohibited for _, value in target
                )
                if failed:
                    findings.append(_rule_finding(package, rule, targets["pointer"]))
            continue
        for resolved_pointer, actual in values:
            match = re.match(r"/guias/(\d+)", resolved_pointer)
            if (
                rule.get("tipo_guia")
                and match
                and lote.get("guias", [])[int(match.group(1))].get("tipo") != rule["tipo_guia"]
            ):
                continue
            failed = False
            if kind == "padrao":
                failed = not isinstance(actual, str) or re.fullmatch(check["regex"], actual) is None
            elif kind == "valores":
                failed = actual not in check.get("permitidos", [])
            elif kind == "max_itens":
                failed = not isinstance(actual, list) or len(actual) > check["max"]
            if failed:
                findings.append(_rule_finding(package, rule, resolved_pointer))
    return findings


__all__ = ["RulePackage", "rule_findings", "rules_schema", "validate_package"]
