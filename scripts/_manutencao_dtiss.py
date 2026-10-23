"""Prepara a referência unitária D-TISS da ANS."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import itertools
import json
import logging
import multiprocessing
import shutil
import sqlite3
import tempfile
import time
import urllib.request
import zipfile
from collections import Counter
from collections.abc import Iterator
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from tiss.referencia import _UFS

if __package__:
    from ._manutencao_common import write_json
    from ._manutencao_dtiss_estatisticas import distribuicao, publicar
else:
    from _manutencao_common import write_json
    from _manutencao_dtiss_estatisticas import distribuicao, publicar

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/TISS"
MANIFEST_PATH = ROOT / "src/tiss/referencia/_data/manifesto.json"
OUT = ROOT / "dist/referencia"
ASSET = "referencia-dtiss.sqlite"
ASSET_URL = "https://voa-tiss-dados.s3.sa-east-1.amazonaws.com/publico/referencia/{data}/{nome}"
EXCLUDED_TABLES = frozenset({"00", "90", "98"})
_SCHEMA = """
CREATE TABLE meta (chave TEXT PRIMARY KEY, valor TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE celula (
  codigo TEXT NOT NULL,
  tabela TEXT NOT NULL,
  uf TEXT NOT NULL,
  modalidade TEXT NOT NULL,
  porte TEXT NOT NULL,
  semestre TEXT NOT NULL,
  n INTEGER NOT NULL,
  pacote_pct REAL NOT NULL,
  inf_mediana REAL NOT NULL,
  inf_p25 REAL NOT NULL,
  inf_p75 REAL NOT NULL,
  inf_excluidos_pct REAL NOT NULL,
  pago_n INTEGER,
  pago_mediana REAL,
  pago_p25 REAL,
  pago_p75 REAL,
  pago_excluidos_pct REAL,
  PRIMARY KEY (codigo, tabela, uf, modalidade, porte, semestre)
) WITHOUT ROWID;
"""
_COLS = (
    "ID_EVENTO_ATENCAO_SAUDE",
    "CD_PROCEDIMENTO",
    "CD_TABELA_REFERENCIA",
    "QT_ITEM_EVENTO_INFORMADO",
    "VL_ITEM_EVENTO_INFORMADO",
    "VL_ITEM_PAGO_FORNECEDOR",
    "IND_PACOTE",
    "IND_TABELA_PROPRIA",
)
_CONS_COLS = (
    "ID_EVENTO_ATENCAO_SAUDE",
    "CD_MODALIDADE",
    "NM_MODALIDADE",
    "UF_PRESTADOR",
    "PORTE",
)


def _validar_semestre(value: str) -> tuple[int, int]:
    if (
        not isinstance(value, str)
        or len(value) != 6
        or value[4] != "-"
        or not value[:4].isascii()
        or not value[:4].isdigit()
        or value[5] not in {"1", "2"}
    ):
        raise ValueError(f"Semestre inválido: {value}. Use AAAA-1 ou AAAA-2.")
    try:
        ano = int(value[:4])
        semestre = int(value[5])
    except ValueError as exc:
        raise ValueError(f"Semestre inválido: {value}. Use AAAA-1 ou AAAA-2.") from exc
    if ano < 2023:
        raise ValueError("A referência D-TISS está disponível a partir de 2023.")
    return ano, semestre


def _meses(semestre: str) -> list[str]:
    ano, parte = _validar_semestre(semestre)
    inicio = 1 if parte == 1 else 7
    return [f"{ano}{mes:02d}" for mes in range(inicio, inicio + 6)]


def _nome_arquivo(uf: str, mes: str, tipo: str, dado: str) -> str:
    return f"{uf}_{mes}_{tipo}_{dado}.zip"


def _caminho_origem(origem: Path, uf: str, mes: str, tipo: str, dado: str) -> Path:
    ano = mes[:4]
    categoria = "AMBULATORIAL" if tipo == "AMB" else "HOSPITALAR"
    return origem / categoria / ano / uf / _nome_arquivo(uf, mes, tipo, dado)


def _baixar(url: str, path: Path) -> int:
    tamanho = 0
    with urllib.request.urlopen(url, timeout=180) as resposta, path.open("wb") as destino:
        while bloco := resposta.read(1024 * 1024):
            destino.write(bloco)
            tamanho += len(bloco)
    return tamanho


def _arquivo_zip(
    uf: str,
    mes: str,
    tipo: str,
    dado: str,
    origem: Path | None,
    temporario: Path,
) -> tuple[Path, str, int]:
    nome = _nome_arquivo(uf, mes, tipo, dado)
    if origem is not None:
        caminho = _caminho_origem(origem, uf, mes, tipo, dado)
        if not caminho.is_file():
            raise FileNotFoundError(f"Arquivo D-TISS não encontrado: {caminho}")
        return caminho, nome, 0
    caminho = temporario / nome
    url = f"{BASE_URL}/{'AMBULATORIAL' if tipo == 'AMB' else 'HOSPITALAR'}/{mes[:4]}/{uf}/{nome}"
    tamanho = _baixar(url, caminho)
    return caminho, nome, tamanho


def _decimal(value: str) -> Decimal | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        result = Decimal(raw.replace(".", "").replace(",", "."))
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def _cents(value: str, quantity: str) -> int | None:
    total = _decimal(value)
    count = _decimal(quantity)
    if total is None or count is None or count <= 0:
        return None
    return int((total * 100 / count).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _reader(archive: zipfile.ZipFile) -> tuple[Any, dict[str, int]]:
    member = next((name for name in archive.namelist() if name.lower().endswith(".csv")), None)
    if member is None:
        raise ValueError("O ZIP D-TISS não contém CSV.")
    raw = archive.open(member)
    reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter=";")
    header = next(reader)
    return reader, {name.strip(): index for index, name in enumerate(header)}


def _member_date(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        dates = [
            f"{year:04d}-{month:02d}-{day:02d}"
            for year, month, day, *_ in (info.date_time for info in archive.infolist())
        ]
    return max(dates, default="1970-01-01")


def _arquivo_dados(
    cons_path: Path,
    det_path: Path,
    uf: str,
    partitions: int,
) -> tuple[dict[tuple[str, ...], list[Any]], int, int, int]:
    cells: dict[tuple[str, ...], list[Any]] = {}
    eventos = lidos = usados = 0
    for part in range(partitions):
        eventos_por_id: dict[int, tuple[str, str, str]] = {}
        with zipfile.ZipFile(cons_path) as archive:
            reader, columns = _reader(archive)
            if not set(_CONS_COLS).issubset(columns):
                raise ValueError(f"Colunas ausentes no arquivo CONS: {cons_path.name}")
            for row in reader:
                if not row:
                    continue
                ident = int(row[columns["ID_EVENTO_ATENCAO_SAUDE"]])
                if part == 0:
                    eventos += 1
                if ident % partitions != part:
                    continue
                modalidade = row[columns["NM_MODALIDADE"]].strip()
                porte = row[columns["PORTE"]].strip()
                uf_prestador = row[columns["UF_PRESTADOR"]].strip() or uf
                eventos_por_id[ident] = modalidade, porte, uf_prestador
        with zipfile.ZipFile(det_path) as archive:
            reader, columns = _reader(archive)
            if not set(_COLS).issubset(columns):
                raise ValueError(f"Colunas ausentes no arquivo DET: {det_path.name}")
            for row in reader:
                if not row:
                    continue
                if part == 0:
                    lidos += 1
                ident = int(row[columns["ID_EVENTO_ATENCAO_SAUDE"]])
                if ident % partitions != part:
                    continue
                event = eventos_por_id.get(ident)
                if event is None:
                    continue
                codigo = row[columns["CD_PROCEDIMENTO"]].strip()
                tabela = row[columns["CD_TABELA_REFERENCIA"]].strip()
                if (
                    tabela in EXCLUDED_TABLES
                    or row[columns["IND_TABELA_PROPRIA"]].strip() == "1"
                    or not (codigo.isascii() and codigo.isdigit())
                ):
                    continue
                pacote = row[columns["IND_PACOTE"]].strip() == "1"
                valor = _cents(
                    row[columns["VL_ITEM_EVENTO_INFORMADO"]],
                    row[columns["QT_ITEM_EVENTO_INFORMADO"]],
                )
                quantidade = _decimal(row[columns["QT_ITEM_EVENTO_INFORMADO"]])
                precificado = valor is not None and quantidade is not None and quantidade > 0
                if not pacote and not precificado:
                    continue
                modalidade, porte, uf_prestador = event
                modalidade = modalidade.strip()
                porte = porte.strip()
                cells_for_item = dict.fromkeys(
                    (
                        (codigo, tabela, uf_prestador, modalidade, porte),
                        (codigo, tabela, uf_prestador, modalidade, ""),
                        (codigo, tabela, uf_prestador, "", porte),
                        (codigo, tabela, uf_prestador, "", ""),
                    )
                )
                pago_total = (
                    _decimal(row[columns["VL_ITEM_PAGO_FORNECEDOR"]]) if precificado else None
                )
                pago = (
                    _cents(
                        row[columns["VL_ITEM_PAGO_FORNECEDOR"]],
                        row[columns["QT_ITEM_EVENTO_INFORMADO"]],
                    )
                    if precificado
                    else None
                )
                for key in cells_for_item:
                    cell = distribuicao(cells, key)
                    cell[0] += int(precificado)
                    cell[1] += int(pacote)
                    if precificado:
                        if not pacote:
                            cell[2] += 1
                        cell[3][valor] += 1
                    if pago_total is not None and pago_total > 0 and pago is not None:
                        cell[4][pago] += 1
                usados += 1
    return cells, eventos, lidos, usados


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as arquivo:
        while bloco := arquivo.read(1024 * 1024):
            digest.update(bloco)
    return digest.hexdigest()


def _processar_uf(job: tuple[str, list[str], str | None, int]) -> dict[str, Any]:
    uf, semestres, origem_raw, partitions = job
    inicio = time.perf_counter()
    origem = Path(origem_raw) if origem_raw else None
    with tempfile.TemporaryDirectory(prefix=f"dtiss-{uf}-") as pasta:
        temporario = Path(pasta)
        fontes: dict[str, str] = {}
        datas: list[str] = []
        fontes_por_semestre = {semestre: {} for semestre in semestres}
        datas_por_semestre = {semestre: [] for semestre in semestres}
        acumulados: dict[str, dict[tuple[str, ...], list[Any]]] = {
            semestre: {} for semestre in semestres
        }
        counts = {semestre: [0, 0, 0, 0] for semestre in semestres}
        downloaded = 0
        for semestre in semestres:
            for mes in _meses(semestre):
                for tipo in ("AMB", "HOSP"):
                    cons_path, cons_name, byte_count = _arquivo_zip(
                        uf, mes, tipo, "CONS", origem, temporario
                    )
                    downloaded += byte_count
                    det_path, det_name, byte_count = _arquivo_zip(
                        uf, mes, tipo, "DET", origem, temporario
                    )
                    downloaded += byte_count
                    for path, name in ((cons_path, cons_name), (det_path, det_name)):
                        digest = _hash(path)
                        data = _member_date(path)
                        fontes[name] = digest
                        fontes_por_semestre[semestre][name] = digest
                        datas.append(data)
                        datas_por_semestre[semestre].append(data)
                    cell_data, eventos, lidos, usados = _arquivo_dados(
                        cons_path, det_path, uf, partitions
                    )
                    for key, value in cell_data.items():
                        target = acumulados[semestre].setdefault(
                            (*key, semestre), [0, 0, 0, Counter(), Counter()]
                        )
                        target[0] += value[0]
                        target[1] += value[1]
                        target[2] += value[2]
                        target[3].update(value[3])
                        target[4].update(value[4])
                    counts[semestre][0] += eventos
                    counts[semestre][1] += lidos
                    counts[semestre][2] += usados
                    del cell_data
                    if origem is None:
                        cons_path.unlink()
                        det_path.unlink()
        sem_results = {}
        for semestre in semestres:
            published, suppressed, paid_count = publicar(acumulados[semestre], semestre)
            counts[semestre][3] += suppressed
            sem_results[semestre] = {
                "celulas": published,
                "contagens": {
                    "eventos": counts[semestre][0],
                    "itens_lidos": counts[semestre][1],
                    "itens_usados": counts[semestre][2],
                    "celulas_suprimidas": suppressed,
                    "blocos_pago_publicados": paid_count,
                },
                "fontes": dict(sorted(fontes_por_semestre[semestre].items())),
                "atualizado_em": max(datas_por_semestre[semestre], default="1970-01-01"),
            }
        elapsed = time.perf_counter() - inicio
        logging.info("UF %s concluída em %.1fs (%d bytes)", uf, elapsed, downloaded)
        return {
            "uf": uf,
            "semestres": sem_results,
            "fontes": fontes,
            "datas": datas,
            "bytes_baixados": downloaded,
            "elapsed": elapsed,
        }


def _json_line(value: Any) -> bytes:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{serialized}\n".encode()


def _write_semestre(path: Path, meta: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with (
        path.open("wb") as output,
        gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed,
    ):
        compressed.write(_json_line({"_meta": meta}))
        for row in sorted(
            rows,
            key=lambda item: tuple(
                str(item[key])
                for key in ("codigo", "tabela", "uf", "modalidade", "porte", "semestre")
            ),
        ):
            compressed.write(_json_line(row))


def _ler_meta_semestre(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as compressed:
        return json.loads(next(compressed))["_meta"]


def _ler_linhas(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as compressed:
        next(compressed)
        for line in compressed:
            yield json.loads(line)


def _write_sqlite(
    path: Path,
    meta: dict[str, str],
    rows: Any,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    banco = sqlite3.connect(path)
    banco.execute("PRAGMA page_size = 4096")
    banco.execute("PRAGMA journal_mode = OFF")
    banco.executescript(_SCHEMA)
    banco.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))
    columns = (
        "codigo",
        "tabela",
        "uf",
        "modalidade",
        "porte",
        "semestre",
        "n",
        "pacote_pct",
        "inf_mediana",
        "inf_p25",
        "inf_p75",
        "inf_excluidos_pct",
        "pago_n",
        "pago_mediana",
        "pago_p25",
        "pago_p75",
        "pago_excluidos_pct",
    )
    sql = f"INSERT INTO celula VALUES ({','.join('?' for _ in columns)})"
    banco.executemany(sql, (tuple(row[column] for column in columns) for row in rows))
    banco.commit()
    banco.execute("VACUUM")
    banco.close()


def bake_dtiss(  # noqa: PLR0913
    semestres: list[str],
    *,
    ufs: list[str] | None = None,
    origem: Path | None = None,
    out: Path = OUT,
    manifesto: Path = MANIFEST_PATH,
    workers: int = 8,
    particoes: int = 1,
) -> dict[str, Any]:
    """Gere os arquivos distribuíveis da referência D-TISS."""
    if not semestres:
        raise ValueError("Informe ao menos um semestre.")
    for semestre in semestres:
        _validar_semestre(semestre)
    semestres = sorted(set(semestres))
    selecionadas = sorted(set(ufs or _UFS))
    invalidas = sorted(set(selecionadas) - set(_UFS))
    if invalidas:
        raise ValueError(f"UF inválida: {', '.join(invalidas)}")
    if particoes < 1:
        raise ValueError("--particoes deve ser maior que zero.")
    if workers < 1:
        raise ValueError("--workers deve ser maior que zero.")
    started = time.perf_counter()
    jobs = [(uf, semestres, str(origem) if origem else None, particoes) for uf in selecionadas]
    with multiprocessing.Pool(min(workers, len(jobs))) as pool:
        results = pool.map(_processar_uf, jobs)
    sources_by_semester = {semestre: {} for semestre in semestres}
    dates_by_semester = {semestre: [] for semestre in semestres}
    counts = {
        semestre: {
            "eventos": 0,
            "itens_lidos": 0,
            "itens_usados": 0,
            "celulas_publicadas": 0,
            "celulas_suprimidas": 0,
            "blocos_pago_publicados": 0,
        }
        for semestre in semestres
    }
    bytes_downloaded = sum(result["bytes_baixados"] for result in results)
    for result in results:
        for semestre, data in result["semestres"].items():
            sources_by_semester[semestre].update(data["fontes"])
            dates_by_semester[semestre].append(data["atualizado_em"])
            rows = data["celulas"]
            counts[semestre]["eventos"] += data["contagens"]["eventos"]
            counts[semestre]["itens_lidos"] += data["contagens"]["itens_lidos"]
            counts[semestre]["itens_usados"] += data["contagens"]["itens_usados"]
            counts[semestre]["celulas_publicadas"] += len(rows)
            counts[semestre]["celulas_suprimidas"] += data["contagens"]["celulas_suprimidas"]
            counts[semestre]["blocos_pago_publicados"] += data["contagens"][
                "blocos_pago_publicados"
            ]
            result.setdefault("_rows", {}).setdefault(semestre, []).extend(rows)
    sem_dir = out / "semestres"
    for semestre in semestres:
        rows = [row for result in results for row in result.get("_rows", {}).get(semestre, [])]
        info = {
            "semestre": semestre,
            "fontes": dict(sorted(sources_by_semester[semestre].items())),
            "atualizado_em": max(dates_by_semester[semestre], default="1970-01-01"),
            "contagens": counts[semestre],
        }
        _write_semestre(sem_dir / f"{semestre}.jsonl.gz", info, rows)
    all_sources: dict[str, str] = {}
    all_dates: list[str] = []
    all_counts = {key: 0 for key in next(iter(counts.values()))}
    all_semesters = []
    paths = sorted(sem_dir.glob("*.jsonl.gz"))
    infos = [_ler_meta_semestre(path) for path in paths]
    for info in infos:
        all_semesters.append(info["semestre"])
        all_sources.update(info["fontes"])
        all_dates.append(info["atualizado_em"])
        for key, value in info["contagens"].items():
            all_counts[key] = all_counts.get(key, 0) + value
    updated = max(all_dates, default="1970-01-01")
    fonte = f"ANS, D-TISS: {BASE_URL}"
    db_meta = {
        "fonte": fonte,
        "licenca": "CC BY 4.0, atribuição à ANS",
        "semestres": ",".join(all_semesters),
        "atualizado_em": updated,
    }
    database = out / ASSET
    rows = itertools.chain.from_iterable(_ler_linhas(path) for path in paths)
    _write_sqlite(database, db_meta, rows)
    asset = out / f"{ASSET}.gz"
    with (
        database.open("rb") as source,
        asset.open("wb") as destination,
        gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as target,
    ):
        shutil.copyfileobj(source, target)
    fontes = dict(sorted(all_sources.items()))
    fonte_digest = hashlib.sha256(
        "".join(f"{name} {digest}\n" for name, digest in fontes.items()).encode()
    ).hexdigest()
    manifest = {
        "url": ASSET_URL.format(data=updated, nome=asset.name),
        "sha256": _hash(asset),
        "tamanho": asset.stat().st_size,
        "sqlite_sha256": _hash(database),
        "sqlite_tamanho": database.stat().st_size,
        "atualizado_em": updated,
        "contagens": all_counts,
        "semestres": all_semesters,
        "fontes": fontes,
        "fonte_sha256": fonte_digest,
    }
    write_json(manifesto, manifest)
    logging.info(
        "Total em %.1fs (%d bytes, %d células, %d suprimidas)",
        time.perf_counter() - started,
        bytes_downloaded,
        all_counts["celulas_publicadas"],
        all_counts["celulas_suprimidas"],
    )
    return manifest
