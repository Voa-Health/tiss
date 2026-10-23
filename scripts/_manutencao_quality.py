"""Verificações de qualidade do repositório."""

from __future__ import annotations

import ast
import io
import json
import logging
import re
import subprocess
import tokenize
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
LIMITES = {
    "docstring_chars": 88,
    "comment_chars": 88,
    "comment_lines": 2,
    "module_lines": 600,
    "test_files": 8,
    "test_functions": 37,
    "notebook_output_chars": 2000,
}
_SKIP_PATHS = {
    "uv.lock",
    "agents/faturista/uv.lock",
    "LICENSE",
    "CODE_OF_CONDUCT.md",
    "scripts/manutencao.py",
    "schemas/openapi.json",
    "web/pnpm-lock.yaml",
}
_ABSOLUTE_PATH_PATTERN = re.compile(r"/home/|/tmp/|/Users/|[A-Za-z]:\\", re.IGNORECASE)
_INLINE_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))")
_REFERENCE_LINK_PATTERN = re.compile(r"^\s*\[[^\]]+\]:\s*(?:<([^>]+)>|([^\s]+))", re.MULTILINE)


def _repository_files() -> list[Path]:
    tracked = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return sorted(ROOT / name for name in tracked if (ROOT / name).is_file())


def _text_files(skip_prefixes: tuple[str, ...]) -> list[Path]:
    return [
        path
        for path in _repository_files()
        if path.relative_to(ROOT).as_posix() not in _SKIP_PATHS
        and not path.relative_to(ROOT).as_posix().startswith(skip_prefixes)
        and not (
            path.relative_to(ROOT).as_posix().startswith("src/tiss/")
            and "_data" in path.relative_to(ROOT).parts[2:-1]
        )
    ]


def _report_violation(path: Path | str, line: int, message: str) -> None:
    location = Path(path)
    if location.is_absolute():
        location = location.relative_to(ROOT)
    logging.error("%s:%d: %s", location.as_posix(), line, message)


def _check_style(pattern: re.Pattern[str], skip_prefixes: tuple[str, ...]) -> bool:
    clean = True
    for path in _text_files(skip_prefixes):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = pattern.search(line)
            if match:
                _report_violation(path, line_number, f"termo não permitido: {match.group()}")
                clean = False
    return clean


def _check_readme_snippet() -> bool:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    sections = readme.split("## Início rápido", maxsplit=1)
    if len(sections) != 2:
        _report_violation("README.md", 1, "seção de início rápido ausente")
        return False
    snippet = re.search(r"```python\s*\n(.*?)```", sections[1], flags=re.DOTALL)
    if snippet is None:
        _report_violation("README.md", 1, "bloco Python ausente")
        return False
    path = ROOT / "docs/tutoriais/01-validar-um-lote.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    first_code = next((cell for cell in notebook["cells"] if cell["cell_type"] == "code"), None)
    notebook_source = "".join(first_code["source"]) if first_code else ""
    if snippet.group(1).strip() != notebook_source.strip():
        _report_violation("README.md", 1, "exemplo difere da célula do tutorial 01")
        return False
    return True


def _check_release_versions() -> bool:
    init_path = ROOT / "src/tiss/__init__.py"
    version_match = re.search(
        r"""^__version__\s*=\s*["']([^"']+)["']""",
        init_path.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    if version_match is None:
        _report_violation(init_path, 1, "versão do pacote ausente")
        return False
    package_version = version_match.group(1)
    server_path = ROOT / "server.json"
    server = json.loads(server_path.read_text(encoding="utf-8"))
    clean = True
    if server.get("version") != package_version:
        _report_violation(server_path, 1, "versão difere do pacote")
        clean = False
    for package in server.get("packages", []):
        if package.get("version") != package_version:
            _report_violation(server_path, 1, "versão do pacote MCP difere do pacote")
            clean = False
        for argument in package.get("runtimeArguments", []):
            value = argument.get("value", "")
            match = re.search(r"tiss\[[^]]+\]==([^\s]+)", value)
            if match is not None and match.group(1) != package_version:
                _report_violation(server_path, 1, "versão do extra MCP difere do pacote")
                clean = False
    action_path = ROOT / "action.yml"
    action = yaml.safe_load(action_path.read_text(encoding="utf-8"))
    action_version = action.get("inputs", {}).get("version", {}).get("default")
    if action_version != package_version:
        _report_violation(action_path, 1, "versão padrão difere do pacote")
        clean = False
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if f"mcp-name: {server.get('name')}" not in readme:
        _report_violation(readme_path, 1, "nome MCP ausente ou diferente do registro")
        clean = False
    return clean


def _python_files() -> list[Path]:
    return sorted(
        path
        for folder in ("src", "scripts", "tests", "agents")
        for path in (ROOT / folder).rglob("*.py")
        if ".venv" not in path.parts
    )


def _check_docstrings(path: Path, text: str) -> bool:
    clean = True
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as error:
        _report_violation(path, error.lineno or 1, "sintaxe Python inválida")
        return False
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if docstring is None:
            continue
        line = node.body[0].lineno if node.body else 1
        if len(docstring.splitlines()) != 1:
            _report_violation(path, line, "docstring deve ocupar uma linha")
            clean = False
        if len(docstring) > LIMITES["docstring_chars"]:
            _report_violation(path, line, f"docstring > {LIMITES['docstring_chars']} caracteres")
            clean = False
        if not docstring.endswith("."):
            _report_violation(path, line, "docstring deve terminar com ponto")
            clean = False
    return clean


def _ignored_comment(comment: str) -> bool:
    return (
        comment.startswith("#!")
        or re.search(r"coding[:=]\s*[-\w.]+", comment, re.IGNORECASE) is not None
        or re.match(r"#\s*(?:type\s*:|noqa\b|pragma\b)", comment, re.IGNORECASE) is not None
    )


def _check_comment_length(path: Path, line: int, comment: str) -> bool:
    if len(comment) > LIMITES["comment_chars"]:
        _report_violation(path, line, f"comentário > {LIMITES['comment_chars']} caracteres")
        return False
    return True


def _check_consecutive_comments(path: Path, comment_lines: set[int]) -> bool:
    clean = True
    consecutive = 0
    previous = 0
    for line in sorted(comment_lines):
        consecutive = consecutive + 1 if line == previous + 1 else 1
        if consecutive > LIMITES["comment_lines"]:
            _report_violation(path, line, "comentários consecutivos excedem o limite")
            clean = False
        previous = line
    return clean


def _check_comments(path: Path, text: str) -> bool:
    clean = True
    source_lines = text.splitlines()
    comment_lines: set[int] = set()
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for token in tokens:
            if token.type != tokenize.COMMENT or _ignored_comment(token.string):
                continue
            line, column = token.start
            if not _check_comment_length(path, line, token.string):
                clean = False
            if not source_lines[line - 1][:column].strip():
                comment_lines.add(line)
    except (IndentationError, tokenize.TokenError):
        return clean
    if not _check_consecutive_comments(path, comment_lines):
        clean = False
    return clean


def _check_web_comments() -> bool:
    clean = True
    web = ROOT / "web"
    paths = sorted((*web.rglob("*.ts"), *web.rglob("*.tsx")))
    for path in paths:
        if {"node_modules", ".next"} & set(path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        comment_lines: set[int] = set()
        for match in re.finditer(r"(^|\s)//[^\n]*|/\*.*?\*/", text, re.MULTILINE | re.DOTALL):
            comment = match.group().strip()
            start = text.count("\n", 0, match.start()) + 1
            if not _check_comment_length(path, start, comment):
                clean = False
            comment_lines.update(range(start, start + comment.count("\n") + 1))
        if not _check_consecutive_comments(path, comment_lines):
            clean = False
    return clean


def _check_python_limits() -> bool:
    clean = True
    source_root = ROOT / "src"
    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        if not _check_comments(path, text):
            clean = False
        if path.is_relative_to(source_root):
            line_count = len(text.splitlines())
            if line_count > LIMITES["module_lines"]:
                _report_violation(path, line_count, "módulo excede o limite de linhas")
                clean = False
            if not _check_docstrings(path, text):
                clean = False
    return clean


def _check_test_limits() -> bool:
    clean = True
    files = sorted([*ROOT.glob("tests/test_*.py"), *ROOT.glob("agents/*/tests/test_*.py")])
    if len(files) > LIMITES["test_files"]:
        _report_violation("tests", 1, f"arquivos {len(files)}/{LIMITES['test_files']}")
        clean = False
    count = 0
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        count += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in ast.walk(tree)
        )
    if count > LIMITES["test_functions"]:
        _report_violation("tests", 1, f"funções {count}/{LIMITES['test_functions']}")
        clean = False
    return clean


def _strip_execution_metadata(value: Any) -> None:
    if isinstance(value, dict):
        value.pop("execution", None)
        for item in value.values():
            _strip_execution_metadata(item)
    elif isinstance(value, list):
        for item in value:
            _strip_execution_metadata(item)


def _normalise_notebook(notebook: dict[str, Any]) -> str:
    metadata = notebook.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        notebook["metadata"] = metadata
    metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    metadata["language_info"] = {"name": "python"}
    _strip_execution_metadata(notebook)
    return json.dumps(notebook, ensure_ascii=False, indent=1) + "\n"


def normalise_notebooks(*, check: bool) -> bool:
    clean = True
    for path in sorted((ROOT / "docs" / "tutoriais").glob("*.ipynb")):
        try:
            original = path.read_text(encoding="utf-8")
            notebook = json.loads(original)
        except (OSError, json.JSONDecodeError):
            _report_violation(path, 1, "notebook JSON inválido")
            clean = False
            continue
        if not isinstance(notebook, dict):
            _report_violation(path, 1, "notebook deve conter um objeto JSON")
            clean = False
            continue
        payload = _normalise_notebook(notebook)
        if original == payload:
            continue
        if check:
            _report_violation(path, 1, "notebook não normalizado; rode artefatos")
            clean = False
        else:
            path.write_text(payload, encoding="utf-8")
    return clean


def _check_notebook_source(path: Path, index: int, cell: dict[str, Any]) -> bool:
    source = cell.get("source", "")
    source = "".join(source) if isinstance(source, list) else str(source)
    if _ABSOLUTE_PATH_PATTERN.search(source):
        _report_violation(path, index, f"caminho absoluto na célula {index}")
        return False
    return True


def _check_notebook_output(path: Path, index: int, output: dict[str, Any]) -> bool:
    rendered = json.dumps(output, ensure_ascii=False)
    clean = True
    if _ABSOLUTE_PATH_PATTERN.search(rendered):
        _report_violation(path, index, f"caminho absoluto na saída {index}")
        clean = False
    if len(rendered) > LIMITES["notebook_output_chars"]:
        _report_violation(path, index, f"saída > {LIMITES['notebook_output_chars']} caracteres")
        clean = False
    return clean


def _check_notebook_code_cell(path: Path, index: int, cell: dict[str, Any]) -> bool:
    clean = True
    if cell.get("execution_count") is None:
        _report_violation(path, index, f"célula de código {index} não executada")
        clean = False
    outputs = cell.get("outputs", [])
    if not outputs:
        _report_violation(path, index, f"célula de código {index} sem saída")
        clean = False
    for output in outputs:
        if not _check_notebook_output(path, index, output):
            clean = False
    return clean


def _check_notebook(path: Path) -> bool:
    try:
        original = path.read_text(encoding="utf-8")
        notebook = json.loads(original)
    except (OSError, json.JSONDecodeError):
        _report_violation(path, 1, "notebook JSON inválido")
        return False
    if not isinstance(notebook, dict):
        _report_violation(path, 1, "notebook deve conter um objeto JSON")
        return False
    clean = True
    if original != _normalise_notebook(notebook):
        _report_violation(path, 1, "notebook não normalizado; rode artefatos")
        clean = False
    for index, cell in enumerate(notebook.get("cells", []), start=1):
        if not _check_notebook_source(path, index, cell):
            clean = False
        if cell.get("cell_type") == "code" and not _check_notebook_code_cell(path, index, cell):
            clean = False
    return clean


def _check_notebooks() -> bool:
    clean = True
    for path in sorted((ROOT / "docs" / "tutoriais").glob("*.ipynb")):
        if not _check_notebook(path):
            clean = False
    return clean


def _link_destinations(text: str) -> list[tuple[int, str]]:
    destinations = []
    for pattern in (_INLINE_LINK_PATTERN, _REFERENCE_LINK_PATTERN):
        for match in pattern.finditer(text):
            destination = match.group(1) or match.group(2)
            destinations.append((text.count("\n", 0, match.start()) + 1, destination))
    return destinations


def _check_markdown_links() -> bool:
    clean = True
    files = [path for path in _repository_files() if path.suffix.lower() == ".md"]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for line, destination in _link_destinations(text):
            parsed = urlsplit(destination)
            if parsed.scheme or destination.startswith("/") or not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            try:
                target.relative_to(ROOT)
            except ValueError:
                target = ROOT / "__outside_repository__"
            if not target.exists():
                _report_violation(path, line, f"link relativo não encontrado: {destination}")
                clean = False
    return clean


def verificar(
    style_pattern: re.Pattern[str],
    skip_prefixes: tuple[str, ...],
    artifact_check: Callable[[], bool],
) -> int:
    checks = (
        _check_python_limits(),
        _check_web_comments(),
        _check_test_limits(),
        _check_notebooks(),
        _check_markdown_links(),
        _check_style(style_pattern, skip_prefixes),
        _check_readme_snippet(),
        _check_release_versions(),
        artifact_check(),
    )
    if all(checks):
        logging.info("Padrões, exemplo e artefatos verificados")
        return 0
    return 1
