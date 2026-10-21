"""Preparação da rede hospitalar das operadoras (dados abertos da ANS)."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import multiprocessing
import sqlite3
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

if __package__:
    from ._manutencao_common import sha256, write_json
else:
    from _manutencao_common import sha256, write_json

ROOT = Path(__file__).resolve().parents[1]
REDE_URL = (
    "https://dadosabertos.ans.gov.br/FTP/PDA/produtos_e_prestadores_hospitalares/"
    "produtos_e_prestadores_hospitalares.zip"
)
REDE_PAGE = "https://dados.gov.br/dados/conjuntos-dados/produtos-e-prestadores-hospitalares"
REDE_MANIFEST = ROOT / "src/voa_tiss/rede/_data/manifesto.json"
REDE_OUT = ROOT / "dist/rede"
REDE_ASSET = "rede-hospitalar.sqlite"
ASSET_URL = "https://voa-tiss-dados.s3.sa-east-1.amazonaws.com/publico/rede/{data}/{nome}"
_MIN_FIELDS = 30
_SCHEMA = """
CREATE TABLE meta (chave TEXT PRIMARY KEY, valor TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE estabelecimento (
  id INTEGER PRIMARY KEY,
  cnes TEXT,
  cnpj TEXT,
  nome TEXT NOT NULL,
  classe TEXT,
  cd_municipio TEXT,
  uf TEXT NOT NULL
);
CREATE TABLE vinculo (
  registro_ans TEXT NOT NULL,
  estabelecimento INTEGER NOT NULL REFERENCES estabelecimento(id),
  tipo_contrato TEXT NOT NULL,
  disponibilidade TEXT NOT NULL,
  tipo_prestador TEXT NOT NULL,
  urgencia_emergencia INTEGER NOT NULL,
  dt_vinculo_inicio TEXT,
  planos INTEGER NOT NULL,
  PRIMARY KEY (registro_ans, estabelecimento)
) WITHOUT ROWID;
"""
_INDEXES = """
CREATE INDEX estabelecimento_cnes ON estabelecimento(cnes);
CREATE INDEX estabelecimento_cnpj ON estabelecimento(cnpj);
CREATE INDEX vinculo_estabelecimento ON vinculo(estabelecimento);
"""


def _informado(value: str) -> str:
    # A ANS publica "Nao inform" ou "Nao informado" quando o campo está vazio na origem.
    return "" if value.casefold().startswith("nao inform") else value.strip()


def _digits(value: str, size: int) -> str | None:
    value = value.strip()
    return value.zfill(size) if value.isdigit() else None


def _read_member(
    job: tuple[str, str],
) -> tuple[
    dict[str, Counter[tuple[Any, ...]]],
    dict[Any, Any],
    set[str],
]:
    archive, name = job
    estabelecimentos: dict[str, Counter[tuple[Any, ...]]] = {}
    vinculos: dict[tuple[str, str], list[Any]] = {}
    datas: set[str] = set()
    with zipfile.ZipFile(archive) as bundle, bundle.open(name) as raw:
        reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""), delimiter=";")
        col = {field: index for index, field in enumerate(next(reader))}
        for row in reader:
            if len(row) < _MIN_FIELDS:
                continue
            datas.add(row[col["DT_ATUALIZACAO"]])
            fim = row[col["DT_VINCULO_FIM"]].strip()
            if fim and fim <= row[col["DT_ATUALIZACAO"]]:
                continue
            atributos = (
                _digits(row[col["CD_CNES"]], 7),
                _digits(row[col["CD_CNPJ_ESTB_SAUDE"]], 14),
                row[col["NM_ESTABELECIMENTO_SAUDE"]].strip(),
                _informado(row[col["DE_CLAS_ESTB_SAUDE"]]) or None,
                row[col["CD_MUNICIPIO"]].strip() or None,
                row[col["SG_UF"]].strip(),
            )
            # ID_ESTABELECIMENTO_SAUDE identifica o vínculo, não o estabelecimento.
            ident = (
                f"C{atributos[0]}"
                if atributos[0]
                else f"J{atributos[1]}"
                if atributos[1]
                else f"I{row[col['ID_ESTABELECIMENTO_SAUDE']]}"
            )
            estabelecimentos.setdefault(ident, Counter())[atributos] += 1
            chave = (row[col["CD_OPERADORA"]].strip().zfill(6), ident)
            vinculo = vinculos.get(chave)
            if vinculo is None:
                vinculo = vinculos[chave] = [set(), set(), set(), 0, None, set()]
            for slot, field in enumerate(
                ("DE_TIPO_CONTRATO", "DE_DISPONIBILIDADE", "DE_TIPO_PRESTADOR")
            ):
                value = _informado(row[col[field]])
                if value:
                    vinculo[slot].add(value)
            vinculo[3] = max(vinculo[3], int(row[col["LG_URGENCIA_EMERGENCIA"]] == "1"))
            inicio = row[col["DT_VINCULO_INICIO"]].strip()
            if inicio and (vinculo[4] is None or inicio < vinculo[4]):
                vinculo[4] = inicio
            vinculo[5].add(row[col["ID_PLANO"]])
    return estabelecimentos, vinculos, datas


def _merge(
    results: list[Any],
) -> tuple[
    dict[str, Counter[tuple[Any, ...]]],
    dict[Any, list[Any]],
    set[str],
]:
    estabelecimentos: dict[str, Counter[tuple[Any, ...]]] = {}
    vinculos: dict[tuple[str, str], list[Any]] = {}
    datas: set[str] = set()
    for parcial_estab, parcial_vinc, parcial_datas in results:
        datas |= parcial_datas
        for ident, variantes in parcial_estab.items():
            estabelecimentos.setdefault(ident, Counter()).update(variantes)
        for chave, vinculo in parcial_vinc.items():
            atual = vinculos.get(chave)
            if atual is None:
                vinculos[chave] = vinculo
                continue
            for slot in (0, 1, 2, 5):
                atual[slot] |= vinculo[slot]
            atual[3] = max(atual[3], vinculo[3])
            atual[4] = min(filter(None, (atual[4], vinculo[4])), default=None)
    return estabelecimentos, vinculos, datas


def _mais_frequente(variantes: Counter[tuple[Any, ...]]) -> tuple[Any, ...]:
    return min(variantes.items(), key=lambda item: (-item[1], str(item[0])))[0]


def _write_sqlite(path: Path, meta: dict[str, str], estabelecimentos: Any, vinculos: Any) -> None:
    ids = {chave: index for index, chave in enumerate(sorted(estabelecimentos), start=1)}
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA page_size = 4096")
    db.execute("PRAGMA journal_mode = OFF")
    db.executescript(_SCHEMA)
    db.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))
    db.executemany(
        "INSERT INTO estabelecimento VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            (ids[chave], *_mais_frequente(estabelecimentos[chave]))
            for chave in sorted(estabelecimentos)
        ),
    )
    db.executemany(
        "INSERT INTO vinculo VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            (
                registro,
                ids[chave],
                "|".join(sorted(v[0])),
                "|".join(sorted(v[1])),
                "|".join(sorted(v[2])),
                v[3],
                v[4],
                len(v[5]),
            )
            for (registro, chave), v in sorted(vinculos.items())
        ),
    )
    db.executescript(_INDEXES)
    db.commit()
    db.execute("VACUUM")
    db.close()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def bake_rede(
    archive: Path, out: Path, manifest: Path, *, workers: int | None = None
) -> dict[str, Any]:
    """Gere o SQLite da rede, a cópia compactada e o manifesto."""
    with zipfile.ZipFile(archive) as bundle:
        members = sorted(name for name in bundle.namelist() if name.casefold().endswith(".csv"))
    jobs = [(str(archive), name) for name in members]
    with multiprocessing.Pool(workers) as pool:
        estabelecimentos, vinculos, datas = _merge(pool.map(_read_member, jobs))
    if len(datas) != 1:
        raise ValueError(f"DT_ATUALIZACAO divergente entre arquivos: {sorted(datas)}")
    atualizado_em = datas.pop()
    contagens = {
        "vinculos": len(vinculos),
        "operadoras": len({registro for registro, _ in vinculos}),
        "estabelecimentos": len(estabelecimentos),
        "estabelecimentos_com_cnpj": sum(
            1 for value in estabelecimentos.values() if _mais_frequente(value)[1]
        ),
    }
    meta = {
        "atualizado_em": atualizado_em,
        "fonte": f"ANS, Produtos e Prestadores Hospitalares: {REDE_PAGE}",
        "licenca": "CC BY, atribuição à ANS",
        **{key: str(value) for key, value in contagens.items()},
    }
    out.mkdir(parents=True, exist_ok=True)
    database = out / REDE_ASSET
    _write_sqlite(database, meta, estabelecimentos, vinculos)
    raw = database.read_bytes()
    packed = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=packed, mtime=0) as target:
        target.write(raw)
    asset = out / f"{REDE_ASSET}.gz"
    asset.write_bytes(packed.getvalue())
    result = {
        "url": ASSET_URL.format(data=atualizado_em, nome=asset.name),
        "sha256": _sha256(packed.getvalue()),
        "tamanho": len(packed.getvalue()),
        "sqlite_sha256": _sha256(raw),
        "sqlite_tamanho": len(raw),
        "atualizado_em": atualizado_em,
        "fonte_sha256": sha256(archive),
        "contagens": contagens,
    }
    write_json(manifest, result)
    return result
