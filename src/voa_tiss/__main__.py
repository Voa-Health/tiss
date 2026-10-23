"""CLI para operações locais do voa-tiss."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast

from ._audit import AuditContext
from ._mapa import rejection_map
from ._mapa_html import render_rejection_map_html
from ._rules import validate_package

_MAP_URL = "https://tiss-api.voa.health/v1/rejection-map/submit"


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
    parser = argparse.ArgumentParser(description="Gera um mapa agregado de rejeição.")
    commands = parser.add_subparsers(dest="command", required=True)
    mapa = commands.add_parser("mapa", help="agrega achados por prestador")
    mapa.add_argument("pasta", type=Path)
    mapa.add_argument("--regras", type=Path)
    mapa.add_argument("--contexto", type=Path)
    mapa.add_argument("--html", type=Path)
    mapa.add_argument("--json", type=Path)
    mapa.add_argument("--enviar", action="store_true")
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


def main(argv: list[str] | None = None) -> int:
    """Executa a CLI e retorna seu código de saída."""
    args = _arguments(argv)
    url: str | None
    if args.enviar:
        url = os.environ.get("VOA_TISS_MAPA_URL", _MAP_URL)
        key = os.environ.get("VOA_TISS_KEY")
        if not url or not key:
            sys.stderr.write("Defina VOA_TISS_KEY para enviar o mapa.\n")
            return 2
    else:
        url = key = None

    secret = os.environ.get("VOA_TISS_SEGREDO_PSEUDONIMO")
    if args.enviar and not secret:
        secret = _org_secret(url or _MAP_URL, key or "")
        if secret is None:
            return 2

    if not args.pasta.is_dir():
        sys.stderr.write("A pasta informada não existe ou não é um diretório.\n")
        return 2
    try:
        rules = _json_file(args.regras) if args.regras else None
        if rules is not None:
            errors = validate_package(rules)
            if errors:
                sys.stderr.write(f"Pacote de regras inválido: {' '.join(errors)}\n")
                return 2
        contexto = cast(AuditContext | None, _json_file(args.contexto)) if args.contexto else None
        if contexto is not None and not isinstance(contexto, dict):
            sys.stderr.write("O contexto deve ser um objeto JSON.\n")
            return 2
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
        return 2
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        del exc
        sys.stderr.write("Não foi possível ler as entradas do mapa.\n")
        return 2

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
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
