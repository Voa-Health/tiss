"""Preparação do conjunto TUSS da ANS."""

from __future__ import annotations

import argparse
import logging
import zipfile
from pathlib import Path
from typing import Any

from tiss._text import fold_ascii

if __package__:
    from ._manutencao_ans import _table_id
    from ._manutencao_common import read_csv, write_json
else:
    from _manutencao_ans import _table_id
    from _manutencao_common import read_csv, write_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "src" / "tiss" / "tuss" / "_data" / "tuss.json"
DATASET_VERSION = 1
DATASET_SOURCE = "ANS — Terminologia Unificada da Saúde Suplementar (TUSS)"
DATASET_LICENSE = "CC BY-ND — ANS dados abertos (verbatim redistribution only)"

TABLE_LABELS = {
    "18": "Diárias, taxas e gases medicinais",
    "19": "Materiais e OPME",
    "20": "Medicamentos",
    "22": "Procedimentos e eventos em saúde",
}


def _fold_header(value: str | None) -> str:
    return fold_ascii(value or "")


def _norm(value: str | None) -> str:
    return " ".join(str(value).split()) if value else ""


def _table_sort_key(tabela: str) -> tuple[int, str]:
    value = str(tabela)
    return (0, f"{int(value):09d}") if value.isdigit() else (1, value)


def _normalise_date(value: str | None) -> str:
    raw = _norm(value)
    if not raw:
        return ""
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return raw
    parts = raw.split(" ")[0].split("T")[0].split("/")
    if len(parts) != 3 or len(parts[2]) != 4:
        return ""
    try:
        day, month, year = (int(part) for part in parts)
    except ValueError:
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"


def _detect_columns(headers: list[str]) -> dict[str, str]:
    folded = {header: _fold_header(header) for header in headers}
    resolved: dict[str, str] = {}

    def claim(field: str, predicate) -> None:
        if field in resolved:
            return
        for header, value in folded.items():
            if header not in resolved.values() and predicate(value):
                resolved[field] = header
                return

    claim("codigo", lambda value: value in {"codigo do termo", "codigo tuss", "codigo"})
    claim("codigo", lambda value: value.startswith("codigo") and "tabela" not in value)
    claim("termo", lambda value: value == "termo")
    claim("termo", lambda value: value.startswith("termo") and "reduzid" not in value)
    claim("descricao", lambda value: value in {"descricao", "descricao do termo"})
    claim("descricao", lambda value: "descricao" in value)
    claim("descricao", lambda value: value.startswith("termo reduzid"))
    claim("vigencia_inicio", lambda value: "vigencia" in value and "inicio" in value)
    claim("vigencia_inicio", lambda value: value.startswith("inicio"))
    claim("vigencia_fim", lambda value: "vigencia" in value and "fim" in value)
    claim("vigencia_fim", lambda value: value.startswith("fim"))
    missing = [field for field in ("codigo", "termo") if field not in resolved]
    if missing:
        raise ValueError(f"Coluna obrigatória ausente {missing}; cabeçalhos: {headers}")
    return resolved


def _build_record(
    row: dict[str, str], *, tabela: str, columns: dict[str, str]
) -> dict[str, Any] | None:
    codigo = _norm(row.get(columns["codigo"]))
    if not codigo:
        return None
    return {
        "tabela": str(tabela),
        "codigo": codigo,
        "termo": _norm(row.get(columns["termo"])),
        "descricao": _norm(row.get(columns["descricao"])) if "descricao" in columns else "",
        "vigencia_inicio": _normalise_date(row.get(columns.get("vigencia_inicio", ""))),
        "vigencia_fim": _normalise_date(row.get(columns.get("vigencia_fim", ""))),
    }


def bake_table(
    *, tabela: str, input_csv: Path, encoding: str, delimiter: str
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    rows = read_csv(input_csv, encoding=encoding, delimiter=delimiter)
    columns = _detect_columns(list(rows[0]) if rows else [])
    logging.info("Tabela %s: colunas %s", tabela, columns)
    records.extend(
        record
        for row in rows
        if (record := _build_record(row, tabela=tabela, columns=columns)) is not None
    )
    logging.info("Tabela %s: %d registros", tabela, len(records))
    return records


def _finalise(records: list[dict[str, Any]], *, table_ids: list[str]) -> dict[str, Any]:
    records.sort(key=lambda record: (_table_sort_key(record["tabela"]), record["codigo"]))
    return {
        "version": DATASET_VERSION,
        "source": DATASET_SOURCE,
        "license": DATASET_LICENSE,
        "tables": {
            table: TABLE_LABELS.get(table, "")
            for table in sorted(set(table_ids), key=_table_sort_key)
        },
        "records": records,
    }


def write_dataset(dataset: dict[str, Any], out_path: Path) -> None:
    write_json(out_path, dataset)


def bake_tuss_archive(archive: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    table_ids: list[str] = []
    with zipfile.ZipFile(archive) as bundle:
        for name in sorted(bundle.namelist()):
            table = _table_id(name)
            if table not in TABLE_LABELS or not name.casefold().endswith(".csv"):
                continue
            rows = read_csv(bundle.read(name))
            columns = _detect_columns(list(rows[0]) if rows else [])
            table_ids.append(table)
            records.extend(
                record
                for row in rows
                if (record := _build_record(row, tabela=table, columns=columns)) is not None
            )
    if set(table_ids) != set(TABLE_LABELS):
        missing = sorted(set(TABLE_LABELS) - set(table_ids))
        raise ValueError(f"Tabelas TUSS ausentes no arquivo ANS: {missing}")
    return _finalise(records, table_ids=table_ids)


def _parse_table_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--table deve usar ID=CAMINHO")
    table, _, path = value.partition("=")
    if not table.strip() or not path.strip():
        raise argparse.ArgumentTypeError("--table deve usar ID=CAMINHO")
    return table.strip(), Path(path.strip())
