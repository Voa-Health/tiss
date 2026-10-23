"""Interface de linha de comando do tiss."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast

from lxml import etree

import tiss
from tiss import tuss

from ._audit import AuditContext
from ._lote import Lote
from ._mapa import rejection_map
from ._mapa_html import render_rejection_map_html
from ._rules import validate_package
from ._schema import parser as xml_parser

_MAP_URL = "https://tiss-api.voa.health/v1/rejection-map/submit"
_ANS = {"ans": "http://www.ans.gov.br/padroes/tiss/schemas"}
_USAGE_ERROR = 2
_ERROR = 1


def _org_secret(url: str, key: str) -> str | None:
    request = urllib.request.Request(
        url.rsplit("/", 1)[0] + "/config",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            value = json.load(response)
        if isinstance(value, dict) and value.get("enabled") is True:
            secret = value.get("secret")
            if isinstance(secret, str) and re.fullmatch(r"[0-9a-f]{64}", secret):
                return secret
    except (OSError, ValueError, TypeError):
        pass
    sys.stderr.write("Coleta indisponível para esta chave.\n")
    return None


def _json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _inputs(folder: Path) -> tuple[list[str | bytes | dict[str, Any]], list[Path]]:
    paths = sorted(
        (
            path
            for path in folder.rglob("*")
            if path.is_file() and path.suffix.lower() in {".xml", ".json"}
        ),
        key=lambda path: path.as_posix(),
    )
    lotes: list[str | bytes | dict[str, Any]] = []
    for path in paths:
        if path.suffix.lower() == ".xml":
            lotes.append(path.read_bytes())
        else:
            value = _json_file(path)
            if not isinstance(value, dict):
                raise ValueError(f"Arquivo JSON não contém um lote: {path}")
            lotes.append(value)
    return lotes, paths


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida, corrige e consulta documentos TISS.")
    parser.add_argument("--version", action="version", version=f"tiss {tiss.__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="valida arquivos ou pastas")
    validate.add_argument("paths", nargs="+", type=Path)
    validate.add_argument("--operadora")
    validate.add_argument("--format", choices=("text", "json", "github"), default="text")

    fix = commands.add_parser("fix", help="aplica correções determinísticas")
    fix.add_argument("arquivo", type=Path)
    output = fix.add_mutually_exclusive_group()
    output.add_argument("--write", action="store_true")
    output.add_argument("-o", "--output", type=Path)
    fix.add_argument("--operadora")

    hash_command = commands.add_parser("hash", help="calcula o hash do epílogo")
    hash_command.add_argument("arquivo", type=Path)
    hash_command.add_argument("--check", action="store_true")

    glosa = commands.add_parser("glosa", help="consulta um código de glosa")
    glosa.add_argument("codigo")
    tuss_parser = commands.add_parser("tuss", help="consulta um código ou termo TUSS")
    tuss_parser.add_argument("consulta")
    operadora = commands.add_parser("operadora", help="consulta o perfil de uma operadora")
    operadora.add_argument("registro")

    mapa = commands.add_parser("mapa", help="agrega achados por prestador")
    mapa.add_argument("pasta", type=Path)
    mapa.add_argument("--regras", type=Path)
    mapa.add_argument("--contexto", type=Path)
    mapa.add_argument("--html", type=Path)
    mapa.add_argument("--json", type=Path)
    mapa.add_argument("--enviar", action="store_true")

    commands.add_parser("mcp", help="inicia o servidor MCP local em stdio")
    serve = commands.add_parser("serve", help="inicia a API HTTP local")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8000, type=int)
    return parser.parse_args(argv)


def _send_map(url: str, key: str, body: bytes) -> bool:
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        sys.stderr.write("Falha ao enviar o mapa.\n")
        return False
    return True


def _mapa(args: argparse.Namespace) -> int:
    url: str | None
    key: str | None
    if args.enviar:
        url = os.environ.get("TISS_MAPA_URL", _MAP_URL)
        key = os.environ.get("TISS_KEY")
        if not url or not key:
            sys.stderr.write("Defina TISS_KEY para enviar o mapa.\n")
            return _USAGE_ERROR
    else:
        url = key = None

    secret = os.environ.get("TISS_SEGREDO_PSEUDONIMO")
    if args.enviar and not secret:
        secret = _org_secret(url or _MAP_URL, key or "")
        if secret is None:
            return _USAGE_ERROR

    if not args.pasta.is_dir():
        sys.stderr.write("A pasta informada não existe ou não é um diretório.\n")
        return _USAGE_ERROR
    try:
        rules = _json_file(args.regras) if args.regras else None
        if rules is not None:
            errors = validate_package(rules)
            if errors:
                sys.stderr.write(f"Pacote de regras inválido: {' '.join(errors)}\n")
                return _USAGE_ERROR
        contexto = cast(AuditContext | None, _json_file(args.contexto)) if args.contexto else None
        if contexto is not None and not isinstance(contexto, dict):
            sys.stderr.write("O contexto deve ser um objeto JSON.\n")
            return _USAGE_ERROR
        lotes, paths = _inputs(args.pasta)
        result = rejection_map(
            lotes,
            contexto=contexto,
            operadora=rules,
            segredo_pseudonimo=secret,
        )
    except ValueError as exc:
        message = str(exc)
        if message != ("Informe segredo_pseudonimo para lotes com prestador identificado por CPF."):
            message = "Não foi possível gerar o mapa com os dados informados."
        sys.stderr.write(message + "\n")
        return _USAGE_ERROR
    except (OSError, json.JSONDecodeError, TypeError):
        sys.stderr.write("Não foi possível ler as entradas do mapa.\n")
        return _USAGE_ERROR

    for index in result["ignorados"]:
        if index < len(paths):
            sys.stderr.write(f"Lote ignorado: {paths[index]}\n")
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(serialized + "\n", encoding="utf-8")
    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_rejection_map_html(result), encoding="utf-8")
    if not args.json and not args.html:
        sys.stdout.write(serialized + "\n")
    if args.enviar and not _send_map(url or "", key or "", serialized.encode("utf-8")):
        return _ERROR
    return 0


def _report(path: Path, operadora: str | None) -> tuple[tiss.Report, bytes | None]:
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise IsADirectoryError(path)
    content = path.read_bytes()
    if path.suffix.lower() == ".xml":
        return tiss.validate(content, operadora=operadora), content
    if path.suffix.lower() == ".json":
        value = json.loads(content.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"Arquivo JSON não contém um lote: {path}")
        return tiss.check(value, operadora=operadora), None
    raise ValueError(f"Formato de arquivo não suportado: {path}")


def _expand_paths(paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_dir():
            expanded.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in {".xml", ".json"}
            )
        elif path.is_file():
            expanded.append(path)
        else:
            raise ValueError(f"Caminho não é um arquivo ou pasta: {path}")
    return sorted(set(expanded), key=lambda item: item.as_posix())


def _line(root: etree._Element | None, xpath: str | None) -> int | None:
    if root is None or not xpath:
        return None
    try:
        matches = root.xpath(xpath, namespaces=_ANS)
        return matches[0].sourceline if matches and isinstance(matches[0], etree._Element) else None
    except (etree.LxmlError, TypeError, ValueError):
        return None


def _escape_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(value: str) -> str:
    return _escape_data(value).replace(":", "%3A").replace(",", "%2C")


def _format_validation(
    reports: dict[str, tuple[tiss.Report, bytes | None]], output_format: str
) -> int:
    if output_format == "json":
        serialized: Any
        if len(reports) == 1:
            serialized = next(iter(reports.values()))[0].to_dict()
        else:
            serialized = {path: report.to_dict() for path, (report, _) in reports.items()}
        sys.stdout.write(
            json.dumps(serialized, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
    else:
        errors = warnings = 0
        for path, (report, content) in reports.items():
            root: etree._Element | None = None
            if content is not None and report.findings:
                try:
                    root = etree.fromstring(content, xml_parser())
                except (etree.LxmlError, ValueError):
                    root = None
            for finding in report.findings:
                line = _line(root, finding.xpath)
                if finding.severity == "error":
                    errors += 1
                else:
                    warnings += 1
                if output_format == "github":
                    command = "warning" if finding.severity == "warning" else "error"
                    properties = f"file={_escape_property(path)}"
                    if line is not None:
                        properties += f",line={line}"
                    properties += f",title={_escape_property(finding.code)}"
                    sys.stdout.write(f"::{command} {properties}::{_escape_data(finding.message)}\n")
                    continue
                location = f"{path}:{line}" if line is not None else path
                suffix = finding.pointer or finding.xpath
                details = f" ({suffix})" if suffix else ""
                sys.stdout.write(
                    f"{location}: {finding.severity} {finding.code}: {finding.message}{details}\n"
                )
                if finding.needs:
                    sys.stdout.write(f"  needs: {', '.join(finding.needs)}\n")
        if output_format == "text":
            sys.stdout.write(
                f"{errors} erro(s), {warnings} aviso(s) em {len(reports)} arquivo(s)\n"
            )
    return _ERROR if any(not report.valid for report, _ in reports.values()) else 0


def _validate(args: argparse.Namespace) -> int:
    try:
        paths = _expand_paths(args.paths)
        if not paths:
            locations = ", ".join(path.as_posix() for path in args.paths)
            sys.stderr.write(f"Nenhum arquivo .xml ou .json encontrado em: {locations}\n")
            return _USAGE_ERROR
        reports = {path.as_posix(): _report(path, args.operadora) for path in paths}
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"Não foi possível ler a entrada: {exc}\n")
        return _USAGE_ERROR
    return _format_validation(reports, args.format)


def _load_lote(path: Path) -> tuple[dict[str, Any], bytes | None]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    content = path.read_bytes()
    if path.suffix.lower() == ".xml":
        return cast(dict[str, Any], tiss.parse_lote(content)), content
    if path.suffix.lower() == ".json":
        value = json.loads(content.decode("utf-8"))
        if isinstance(value, dict):
            return cast(dict[str, Any], value), None
        raise ValueError("Arquivo JSON não contém um lote.")
    raise ValueError(f"Formato de arquivo não suportado: {path}")


def _serialize_lote(lote: dict[str, Any], path: Path) -> bytes:
    if path.suffix.lower() == ".xml":
        return tiss.build_lote(cast(Lote, lote))
    return (json.dumps(lote, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _fix(args: argparse.Namespace) -> int:
    try:
        lote, original = _load_lote(args.arquivo)
        for _ in range(3):
            report = tiss.check(lote, operadora=args.operadora)
            if not any(finding.fix for finding in report.findings):
                break
            lote = tiss.apply_fixes(lote, report)
        report = tiss.check(lote, operadora=args.operadora)
        output = _serialize_lote(lote, args.arquivo)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"Não foi possível corrigir a entrada: {exc}\n")
        return _USAGE_ERROR
    if args.write or args.output:
        destination = args.arquivo if args.write else args.output
        try:
            destination.write_bytes(output)
        except OSError as exc:
            sys.stderr.write(f"Não foi possível gravar a saída: {exc}\n")
            return _USAGE_ERROR
    else:
        encoding = "ISO-8859-1" if args.arquivo.suffix.lower() == ".xml" else "utf-8"
        old_text = (original or b"").decode(encoding)
        new_text = output.decode(encoding)
        sys.stdout.writelines(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=args.arquivo.as_posix(),
                tofile=args.arquivo.as_posix() + " (corrigido)",
            )
        )
    for finding in report.findings:
        if finding.needs:
            sys.stderr.write(f"needs: {', '.join(finding.needs)}\n")
        if finding.severity == "error":
            sys.stderr.write(f"erro {finding.code}: {finding.message}\n")
    return 0 if report.valid else _ERROR


def _hash(args: argparse.Namespace) -> int:
    try:
        content = args.arquivo.read_bytes()
        calculated = tiss.hash_epilogo(content)
    except (OSError, ValueError, UnicodeError) as exc:
        sys.stderr.write(f"Não foi possível calcular o hash: {exc}\n")
        return _USAGE_ERROR
    if not args.check:
        sys.stdout.write(calculated + "\n")
        return 0
    try:
        root = etree.fromstring(content, xml_parser())
        elements = root.xpath(".//ans:epilogo/ans:hash", namespaces=_ANS)
        actual = (elements[0].text or "") if elements else "(ausente)"
    except (etree.LxmlError, ValueError):
        sys.stderr.write("XML inválido.\n")
        return _USAGE_ERROR
    if actual == calculated:
        sys.stdout.write(calculated + "\n")
        return 0
    sys.stderr.write(f"Hash divergente: calculado {calculated}; encontrado {actual}.\n")
    return _ERROR


def _lookup(args: argparse.Namespace) -> int:
    if args.command == "glosa":
        result = tiss.glosa(args.codigo)
        if result is None:
            sys.stderr.write(f"Glosa não encontrada: {args.codigo}\n")
            return _ERROR
    elif args.command == "tuss":
        results = (
            tuss.lookup(args.consulta, include_expired=True)
            if args.consulta.isdigit()
            else tuss.search(args.consulta, include_expired=False)[:20]
        )
        if not results:
            sys.stderr.write(f"Resultado não encontrado: {args.consulta}\n")
            return _ERROR
        result = {"resultados": results}
    else:
        result = tiss.operadoras.perfil(args.registro)
        if result is None:
            sys.stderr.write(f"Operadora não encontrada: {args.registro}\n")
            return _ERROR
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return 0


def _optional_server(args: argparse.Namespace) -> int:
    try:
        if args.command == "mcp":
            from tiss.server._stdio import main as serve_stdio

            serve_stdio()
        else:
            from tiss.server.__main__ import main as serve_http

            serve_http(["--host", args.host, "--port", str(args.port)])
    except ImportError:
        extra = "mcp" if args.command == "mcp" else "server"
        sys.stderr.write(f'Instale o extra: pip install "tiss[{extra}]"\n')
        return _USAGE_ERROR
    return 0


def main(argv: list[str] | None = None) -> int:
    """Execute a CLI e retorne seu código de saída."""
    try:
        args = _arguments(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    if args.command == "validate":
        return _validate(args)
    if args.command == "fix":
        return _fix(args)
    if args.command == "hash":
        return _hash(args)
    if args.command in {"glosa", "tuss", "operadora"}:
        return _lookup(args)
    if args.command == "mapa":
        return _mapa(args)
    return _optional_server(args)


if __name__ == "__main__":
    raise SystemExit(main())
