"""Utilitários para baixar e abrir bancos públicos verificados."""

from __future__ import annotations

import gzip
import hashlib
import os
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import urlopen

_CHUNK_SIZE = 1024 * 1024


class DadosIndisponiveis(RuntimeError):
    """Indica que dados públicos não puderam ser verificados ou lidos."""

    codigo = "dados_indisponiveis"


def sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    tamanho = 0
    with path.open("rb") as arquivo:
        while bloco := arquivo.read(_CHUNK_SIZE):
            digest.update(bloco)
            tamanho += len(bloco)
    return digest.hexdigest(), tamanho


def caminho_cache(nome: str, manifesto: dict[str, Any]) -> tuple[Path, bool]:
    raiz = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")).expanduser()
    caminho = (raiz / "voa-tiss" / f"{nome}.sqlite").resolve()
    if caminho.is_file():
        digest, tamanho = sha256(caminho)
        if digest == manifesto["sqlite_sha256"] and tamanho == manifesto["sqlite_tamanho"]:
            return caminho, True
    return caminho, False


def validar_manifesto(manifesto: dict[str, Any], erro: type[DadosIndisponiveis]) -> None:
    for chave in ("sha256", "sqlite_sha256"):
        if not isinstance(manifesto.get(chave), str) or not re.fullmatch(
            r"[0-9a-f]{64}", manifesto[chave]
        ):
            raise erro("O manifesto de dados públicos é inválido.")
    for chave in ("tamanho", "sqlite_tamanho"):
        if not isinstance(manifesto.get(chave), int) or manifesto[chave] < 0:
            raise erro("O manifesto de dados públicos é inválido.")
    if not isinstance(manifesto.get("url"), str) or not manifesto["url"]:
        raise erro("O manifesto de dados públicos é inválido.")


def baixar_verificado(
    destino: Path,
    manifesto: dict[str, Any],
    erro: type[DadosIndisponiveis],
    recurso: str,
) -> Path:
    validar_manifesto(manifesto, erro)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporarios: list[Path] = []
    try:
        descritor, nome = tempfile.mkstemp(dir=destino.parent, prefix=f".{recurso}-", suffix=".gz")
        os.close(descritor)
        compactado = Path(nome)
        temporarios.append(compactado)
        digest = hashlib.sha256()
        tamanho = 0
        with urlopen(manifesto["url"], timeout=60) as resposta, compactado.open("wb") as arquivo:
            while bloco := resposta.read(_CHUNK_SIZE):
                arquivo.write(bloco)
                digest.update(bloco)
                tamanho += len(bloco)
        if tamanho != manifesto["tamanho"] or digest.hexdigest() != manifesto["sha256"]:
            raise erro(f"O arquivo compactado de {recurso} não corresponde ao manifesto.")

        descritor, nome = tempfile.mkstemp(
            dir=destino.parent, prefix=f".{recurso}-", suffix=".sqlite"
        )
        os.close(descritor)
        banco_temporario = Path(nome)
        temporarios.append(banco_temporario)
        digest = hashlib.sha256()
        tamanho = 0
        with gzip.open(compactado, "rb") as origem, banco_temporario.open("wb") as arquivo:
            while bloco := origem.read(_CHUNK_SIZE):
                arquivo.write(bloco)
                digest.update(bloco)
                tamanho += len(bloco)
        if (
            tamanho != manifesto["sqlite_tamanho"]
            or digest.hexdigest() != manifesto["sqlite_sha256"]
        ):
            raise erro(f"O banco de {recurso} não corresponde ao manifesto.")
        os.replace(banco_temporario, destino)
        return destino
    except erro:
        raise
    except Exception as exc:
        raise erro(f"Não foi possível baixar e verificar {recurso}.") from exc
    finally:
        for temporario in temporarios:
            temporario.unlink(missing_ok=True)


def conectar(caminho: str, erro: type[DadosIndisponiveis], recurso: str) -> sqlite3.Connection:
    try:
        banco = sqlite3.connect(
            f"{Path(caminho).as_uri()}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        banco.row_factory = sqlite3.Row
        banco.execute("SELECT valor FROM meta LIMIT 1")
        return banco
    except sqlite3.Error as exc:
        raise erro(f"O banco SQLite de {recurso} não pôde ser aberto.") from exc
