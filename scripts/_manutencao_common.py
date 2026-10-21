"""Funções compartilhadas para preparar dados locais."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as target:
        shutil.copyfileobj(response, target)
    return sha256(destination)


def write_json(path: Path, data: Any, *, sort_keys: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=sort_keys, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_csv(
    raw: bytes | Path,
    *,
    delimiter: str = ";",
    encoding: str | None = None,
) -> list[dict[str, str]]:
    source = raw.read_bytes() if isinstance(raw, Path) else raw
    encodings = (
        ("utf-8-sig", "latin-1")
        if encoding is None or encoding.lower() in {"utf-8", "utf-8-sig"}
        else (encoding, "utf-8-sig", "latin-1")
    )
    for codec in dict.fromkeys(encodings):
        try:
            text = source.decode(codec)
        except UnicodeDecodeError:
            continue
        return list(csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter))
    raise ValueError("Codificação CSV não reconhecida")
