"""Implementação enxuta de operações JSON Patch RFC 6902 para lotes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class PatchError(ValueError):
    """A operação JSON Patch não pode ser aplicada ao documento."""


def _tokens(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise PatchError("JSON Pointer inválido")
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]


def _index(token: str, length: int, *, add: bool = False) -> int:
    if add and token == "-":
        return length
    try:
        index = int(token)
    except ValueError as exc:
        raise PatchError("Índice JSON inválido") from exc
    if str(index) != token or index < 0 or index > length or (index == length and not add):
        raise PatchError("Índice JSON fora do documento")
    return index


def _parent(document: Any, tokens: list[str]) -> tuple[Any, str]:
    if not tokens:
        raise PatchError("A operação na raiz não é suportada")
    current = document
    for token in tokens[:-1]:
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list):
            current = current[_index(token, len(current))]
        else:
            raise PatchError("Caminho JSON inexistente")
    return current, tokens[-1]


def _get(document: Any, pointer: str) -> Any:
    current = document
    for token in _tokens(pointer):
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list):
            current = current[_index(token, len(current))]
        else:
            raise PatchError("Caminho JSON inexistente")
    return current


def _apply(document: Any, operation: dict[str, Any]) -> Any:
    op = operation.get("op")
    path = operation.get("path")
    if not isinstance(path, str):
        raise PatchError("Operação sem JSON Pointer")
    if op == "test":
        if _get(document, path) != operation.get("value"):
            raise PatchError("O teste JSON Patch falhou")
        return document
    if op not in {"add", "replace", "remove"}:
        raise PatchError("Operação JSON Patch não suportada")
    tokens = _tokens(path)
    if not tokens:
        if op == "remove":
            raise PatchError("Não é possível remover a raiz")
        if op in {"replace", "add"}:
            return deepcopy(operation.get("value"))
    parent, token = _parent(document, tokens)
    if isinstance(parent, dict):
        if op == "add":
            parent[token] = deepcopy(operation.get("value"))
        elif token not in parent:
            raise PatchError("Caminho JSON inexistente")
        elif op == "replace":
            parent[token] = deepcopy(operation.get("value"))
        else:
            del parent[token]
    elif isinstance(parent, list):
        index = _index(token, len(parent), add=op == "add")
        if op == "add":
            parent.insert(index, deepcopy(operation.get("value")))
        elif op == "replace":
            parent[index] = deepcopy(operation.get("value"))
        else:
            del parent[index]
    else:
        raise PatchError("O pai do caminho JSON não aceita filhos")
    return document


def apply_patch(document: Any, operations: list[dict[str, Any]]) -> Any:
    """Retorna uma cópia corrigida sem alterar o documento original."""
    if not isinstance(operations, list):
        raise PatchError("JSON Patch deve ser uma lista")
    result = deepcopy(document)
    for operation in operations:
        if not isinstance(operation, dict):
            raise PatchError("Operação JSON Patch inválida")
        result = _apply(result, operation)
    return result


def apply_fixes(lote: dict[str, Any], report: Any) -> dict[str, Any]:
    """Aplica as correções dos achados na ordem do relatório e preserva a entrada."""
    result = deepcopy(lote)
    findings = report.findings if hasattr(report, "findings") else report.get("findings", [])
    for finding in findings:
        fix = finding.fix if hasattr(finding, "fix") else finding.get("fix")
        if fix:
            result = apply_patch(result, fix)
    return result


__all__ = ["PatchError", "apply_fixes", "apply_patch"]
