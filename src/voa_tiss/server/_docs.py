from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path
from typing import Any, cast

_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_WORDS = re.compile(r"\w+")


def _load_readme() -> str:
    try:
        return metadata("voa-tiss")["Description"] or ""
    except PackageNotFoundError:
        # Vercel runs from source without package metadata.
        readme = Path(__file__).resolve().parents[3] / "README.md"
        try:
            return readme.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(value.casefold().split())


def _sections(document: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    title = ""
    lines: list[str] = []
    for line in document.splitlines():
        match = _HEADING.match(line)
        if match:
            if lines:
                sections.append((title, "\n".join(lines)))
            title = match.group(1)
            lines = [line]
        else:
            lines.append(line)
    if lines:
        sections.append((title, "\n".join(lines)))
    return sections


def search_docs(corpus: dict[str, str], texto: str, limite: int) -> list[dict[str, str]]:
    terms = [word for word in _WORDS.findall(_fold(texto)) if len(word) >= 2]
    matches: list[tuple[int, str, int, dict[str, str]]] = []
    for uri, document in corpus.items():
        for order, (title, section) in enumerate(_sections(document)):
            folded = _fold(section)
            score = sum(folded.count(term) for term in terms)
            if score:
                matches.append(
                    (
                        -score,
                        uri,
                        order,
                        {"uri": uri, "titulo": title, "trecho": section[:1200]},
                    )
                )
    matches.sort(key=lambda item: item[:3])
    return [item[3] for item in matches[:limite]]


def _escape_markdown(value: str) -> str:
    return value.replace("|", "\\|")


def _prompt_arguments(prompt: dict[str, object]) -> str:
    arguments = cast(list[tuple[str, str, bool]], prompt["arguments"])
    return ", ".join(
        f"`{name}` ({'obrigatório' if required else 'opcional'})" for name, _, required in arguments
    )


def render_api_docs(
    ops: Sequence[Any],
    prompts: dict[str, dict[str, object]],
    resources: Sequence[dict[str, str]],
    templates: Sequence[dict[str, str]],
) -> str:
    rows = """# API HTTP e MCP

Orçamento aproximado: `ceil(tamanho UTF-8 do JSON / 4)` tokens.

| Operação | Rota HTTP | Tool MCP | Descrição | Orçamento |
| --- | --- | --- | --- | ---: |""".splitlines()
    rows.extend(
        f"| `{op.name}` | `{op.method} {op.route}` | `{op.tool_name}` | "
        f"{_escape_markdown(op.description)} | {op.max_tokens} |"
        for op in ops
    )
    rows.extend(
        [
            "",
            "## Acesso",
            "",
            "Sem chave, respondem `sandbox_*` e a lista de espera. As demais exigem uma chave",
            "`sk_tiss_` da organização em `Authorization: Bearer`, criada no painel",
            "`/org`. Não há limite diário.",
            "Chave inválida ou revogada retorna `401`; a revogação vale em até 60 s.",
            "Chave sem o escopo da operação retorna `403`. Cada chamada com chave entra",
            "no uso da organização, por operação e por chave.",
            "",
            "| Escopo | Operações |",
            "| --- | --- |",
        ]
    )
    scopes: dict[str, list[str]] = {}
    for op in ops:
        scopes.setdefault(op.scope or "qualquer chave", []).append(f"`{op.name}`")
    rows.extend(f"| `{scope}` | {', '.join(names)} |" for scope, names in sorted(scopes.items()))
    rows.extend(
        [
            "",
            "| Rota HTTP | Descrição |",
            "| --- | --- |",
            "| `GET /v1/limits` | Regras de acesso. |",
        ]
    )
    rows.extend(
        [
            "",
            "## Lista de espera",
            "",
            "`POST /v1/lista-de-espera` recebe `modulo`, `email`, `empresa`, `volume_mensal`",
            "e, para o extrator, `tipos_documento`. Retorna `202`, `422`, `429` ou `503`.",
            "Nada é gravado; o pedido vai para a ferramenta de análise do produto.",
            "A rota é HTTP e não está disponível como ferramenta MCP.",
        ]
    )
    rows.extend(
        [
            "",
            "## Prompts MCP",
            "",
            "| Nome | Descrição | Argumentos |",
            "| --- | --- | --- |",
        ]
    )
    rows.extend(
        f"| `{name}` | {_escape_markdown(str(prompt['description']))} | "
        f"{_prompt_arguments(prompt)} |"
        for name, prompt in prompts.items()
    )
    rows.extend(
        [
            "",
            "## Resources MCP",
            "",
            "| URI ou template | Descrição |",
            "| --- | --- |",
        ]
    )
    rows.extend(
        f"| `{resource['uri']}` | {_escape_markdown(resource['description'])} |"
        for resource in resources
    )
    rows.extend(
        f"| `{resource['uri_template']}` | {_escape_markdown(resource['description'])} |"
        for resource in templates
    )
    return "\n".join(rows) + "\n"


__all__ = ["_load_readme", "render_api_docs", "search_docs"]
