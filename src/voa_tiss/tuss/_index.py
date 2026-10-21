"""Índice local para consulta TUSS por código e termo."""

from __future__ import annotations

import datetime
import json
import re
from functools import cache
from pathlib import Path
from typing import Any

from .._text import fold_ascii

_DEFAULT_DATA_PATH = Path(__file__).parent / "_data" / "tuss.json"

# As modalidades são expandidas nos dois lados da busca.
_MODALITY_SYNONYMS: dict[str, str] = {
    "ressonancia nuclear magnetica": "rm",
    "ressonancia magnetica": "rm",
    "rnm": "rm",
    "rmn": "rm",
    "tomografia computadorizada": "tc",
    "tomografia": "tc",
    "ultrassonografia": "us",
    "ultra sonografia": "us",
    "ultrassom": "us",
    "ultra som": "us",
    "ecografia": "us",
    "radiografia": "rx",
    "raio x": "rx",
    "raios x": "rx",
}

_MODALITY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"\b{re.escape(phrase)}\b"), abbr)
    for phrase, abbr in sorted(_MODALITY_SYNONYMS.items(), key=lambda kv: len(kv[0]), reverse=True)
]

# Conectivos não acrescentam sinal à busca por todos os termos.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "de",
        "do",
        "da",
        "dos",
        "das",
        "e",
        "ou",
        "com",
        "sem",
        "a",
        "o",
        "as",
        "os",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "por",
        "para",
        "ao",
    }
)


def fold(text: str) -> str:
    """Remove acentos e normaliza caixa e espaços, preservando dígitos."""
    return fold_ascii(text)


def _expand_modalities(folded: str) -> str:
    """Substitui nomes de modalidades por abreviações da ANS."""
    out = folded
    for pattern, abbr in _MODALITY_PATTERNS:
        out = pattern.sub(abbr, out)
    return out


def content_tokens(text: str) -> set[str]:
    """Retorna termos úteis para comparar buscas em qualquer ordem."""
    expanded = _expand_modalities(fold(text))
    return {tok for tok in re.split(r"[^a-z0-9]+", expanded) if tok and tok not in _STOPWORDS}


def _today_iso(today: datetime.date | None) -> str:
    """Resolve a data usada para comparar vigência."""
    day = today if today is not None else datetime.date.today()
    return day.isoformat()


def is_vigente(row: dict[str, Any], today_iso: str) -> bool:
    """Indica se a data está dentro do período de vigência."""
    inicio = row.get("vigencia_inicio") or ""
    fim = row.get("vigencia_fim") or ""
    if inicio and today_iso < inicio:
        return False
    return not (fim and today_iso > fim)


class TussIndex:
    """Índice em memória dos registros TUSS."""

    def __init__(
        self,
        records: list[dict[str, Any]],
        *,
        tables: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._records: list[dict[str, Any]] = records
        self._metadata = dict(metadata or {})
        if tables is not None:
            self._metadata["tables"] = tables
        raw_tables = self._metadata.get("tables")
        self._tables = dict(raw_tables) if isinstance(raw_tables, dict) else {}
        self._by_codigo: dict[tuple[str, str], list[int]] = {}
        self._by_termo: dict[str, list[int]] = {}
        self._token_sets: list[set[str]] = []
        for idx, record in enumerate(records):
            tabela = str(record.get("tabela") or "")
            codigo = fold(record.get("codigo") or "")
            if codigo:
                self._by_codigo.setdefault((tabela, codigo), []).append(idx)
            termo_raw = record.get("termo") or ""
            termo = fold(termo_raw)
            if termo:
                self._by_termo.setdefault(termo, []).append(idx)
            self._token_sets.append(content_tokens(termo_raw))

    @property
    def size(self) -> int:
        return len(self._records)

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata.copy()

    @classmethod
    def from_json_path(cls, path: Path) -> TussIndex:
        """Carrega registros de um arquivo JSON."""
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records") or []
        if not isinstance(records, list):
            records = []
        metadata = {key: value for key, value in payload.items() if key != "records"}
        return cls(records, metadata=metadata)

    def lookup(
        self,
        query: str,
        *,
        tabela: str | None = None,
        include_expired: bool = False,
        today: datetime.date | None = None,
    ) -> list[dict[str, Any]]:
        """Busca registros por código, termo, descrição e tokens."""
        folded = fold(query)
        if not folded:
            return []
        today_iso = _today_iso(today)
        seen: set[int] = set()
        ordered: list[int] = []

        def _emit(indexes: list[int]) -> None:
            for i in indexes:
                if i not in seen:
                    seen.add(i)
                    ordered.append(i)

        if tabela is not None:
            _emit(self._by_codigo.get((str(tabela), folded), []))
        else:
            for (_tab, code), indexes in self._by_codigo.items():
                if code == folded:
                    _emit(indexes)
        _emit(self._by_termo.get(folded, []))
        if not ordered:
            for key, indexes in self._by_termo.items():
                if folded in key:
                    _emit(indexes)
            for i, record in enumerate(self._records):
                descricao = fold(record.get("descricao") or "")
                if descricao and folded in descricao:
                    _emit([i])
        if not ordered:
            q_tokens = content_tokens(query)
            if q_tokens:
                for i, tokens in enumerate(self._token_sets):
                    if q_tokens <= tokens:
                        _emit([i])

        return [
            self._records[i]
            for i in ordered
            if self._passes_filters(
                self._records[i],
                tabela=tabela,
                include_expired=include_expired,
                today_iso=today_iso,
            )
        ]

    def get(
        self,
        codigo: str,
        *,
        tabela: str | None = None,
        include_expired: bool = True,
        today: datetime.date | None = None,
    ) -> list[dict[str, Any]]:
        """Busca correspondências exatas de código, sem busca aproximada."""
        folded = fold(codigo)
        if not folded:
            return []
        today_iso = _today_iso(today)
        seen: set[int] = set()
        ordered: list[int] = []
        if tabela is not None:
            indexes = self._by_codigo.get((str(tabela), folded), [])
        else:
            indexes = [
                i for (_tab, code), idxs in self._by_codigo.items() if code == folded for i in idxs
            ]
        for i in indexes:
            if i not in seen:
                seen.add(i)
                ordered.append(i)
        return [
            self._records[i]
            for i in ordered
            if self._passes_filters(
                self._records[i],
                tabela=tabela,
                include_expired=include_expired,
                today_iso=today_iso,
            )
        ]

    def validate(
        self,
        itens: list[dict[str, Any]],
        *,
        today: datetime.date | None = None,
    ) -> list[dict[str, Any]]:
        """Verifica a existência e vigência de cada item."""
        today_iso = _today_iso(today)
        out: list[dict[str, Any]] = []
        for item in itens or []:
            tabela = str((item or {}).get("tabela") or "")
            codigo = str((item or {}).get("codigo") or "")
            matches = self.get(
                codigo,
                tabela=tabela or None,
                include_expired=True,
                today=today,
            )
            if not matches:
                out.append(
                    {
                        "tabela": tabela,
                        "codigo": codigo,
                        "exists": False,
                        "vigente": False,
                        "reason": "not_found",
                    }
                )
                continue
            row = matches[0]
            vigente = is_vigente(row, today_iso)
            verdict: dict[str, Any] = {
                "tabela": tabela or row.get("tabela", ""),
                "codigo": codigo,
                "exists": True,
                "vigente": vigente,
                "termo": row.get("termo", ""),
            }
            if not vigente:
                verdict["reason"] = "expired"
            out.append(verdict)
        return out

    def tables(self) -> list[dict[str, Any]]:
        """Lista tabelas, nomes e totais de registros."""
        counts: dict[str, int] = {}
        for record in self._records:
            tabela = str(record.get("tabela") or "")
            if tabela:
                counts[tabela] = counts.get(tabela, 0) + 1
        ids = sorted(set(counts) | set(self._tables), key=_table_sort_key)
        return [
            {
                "tabela": tid,
                "nome": self._tables.get(tid, ""),
                "count": counts.get(tid, 0),
            }
            for tid in ids
        ]

    def names(
        self,
        *,
        tabela: str | None = None,
        include_expired: bool = False,
        today: datetime.date | None = None,
    ) -> list[dict[str, Any]]:
        """Lista os registros em ordem de tabela e código."""
        today_iso = _today_iso(today)
        rows = [
            {
                "codigo": record.get("codigo", ""),
                "termo": record.get("termo", ""),
                "tabela": record.get("tabela", ""),
            }
            for record in self._records
            if self._passes_filters(
                record,
                tabela=tabela,
                include_expired=include_expired,
                today_iso=today_iso,
            )
        ]
        rows.sort(key=lambda r: (_table_sort_key(r["tabela"]), str(r["codigo"])))
        return rows

    @staticmethod
    def _passes_filters(
        record: dict[str, Any],
        *,
        tabela: str | None,
        include_expired: bool,
        today_iso: str,
    ) -> bool:
        if tabela is not None and str(record.get("tabela") or "") != str(tabela):
            return False
        return include_expired or is_vigente(record, today_iso)


def _table_sort_key(tabela: str) -> tuple[int, str]:
    """Ordena identificadores de tabela como número ou texto."""
    text = str(tabela)
    return (0, f"{int(text):09d}") if text.isdigit() else (1, text)


@cache
def get_default_index() -> TussIndex:
    """Retorna o índice TUSS carregado sob demanda."""
    return TussIndex.from_json_path(_DEFAULT_DATA_PATH)


__all__ = [
    "TussIndex",
    "content_tokens",
    "fold",
    "get_default_index",
    "is_vigente",
]
