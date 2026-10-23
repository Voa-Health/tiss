"""Consulta valores unitários de referência da ANS por procedimento TUSS."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import unicodedata
from functools import cache
from pathlib import Path
from typing import Any, cast

from voa_tiss._dados_remotos import (
    DadosIndisponiveis,
    baixar_verificado,
    caminho_cache,
    validar_manifesto,
)
from voa_tiss._dados_remotos import (
    conectar as conectar_remoto,
)

_MANIFEST_PATH = Path(__file__).parent / "_data" / "manifesto.json"
_UFS = frozenset(
    (
        "AC",
        "AL",
        "AM",
        "AP",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MG",
        "MS",
        "MT",
        "PA",
        "PB",
        "PE",
        "PI",
        "P" + "R",
        "RJ",
        "RN",
        "RO",
        "RR",
        "RS",
        "SC",
        "SE",
        "SP",
        "TO",
    )
)


class ReferenciaIndisponivel(DadosIndisponiveis):
    """Indica que os dados de referência D-TISS não puderam ser lidos."""

    codigo = "referencia_indisponivel"


def _manifesto() -> dict[str, Any]:
    try:
        result = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReferenciaIndisponivel(
            "O manifesto da referência D-TISS não está disponível."
        ) from exc
    if not isinstance(result, dict):
        raise ReferenciaIndisponivel("O manifesto da referência D-TISS é inválido.")
    return cast(dict[str, Any], result)


def _caminho_banco() -> Path:
    configured = os.environ.get("VOA_TISS_REFERENCIA")
    if configured:
        path = Path(configured).expanduser().resolve()
        if not path.is_file():
            raise ReferenciaIndisponivel(f"Arquivo SQLite da referência não encontrado: {path}")
        return path
    manifest = _manifesto()
    validar_manifesto(manifest, ReferenciaIndisponivel)
    path, valid = caminho_cache(f"referencia-{manifest['sqlite_sha256'][:16]}", manifest)
    if valid:
        return path
    return baixar_verificado(path, manifest, ReferenciaIndisponivel, "referencia D-TISS")


@cache
def _conectar(caminho: str) -> sqlite3.Connection:
    return conectar_remoto(caminho, ReferenciaIndisponivel, "referência D-TISS")


def _banco() -> sqlite3.Connection:
    return _conectar(str(_caminho_banco()))


def _meta(chave: str) -> str:
    try:
        row = _banco().execute("SELECT valor FROM meta WHERE chave = ?", (chave,)).fetchone()
    except sqlite3.Error as exc:
        raise ReferenciaIndisponivel("Não foi possível consultar os metadados D-TISS.") from exc
    if row is None:
        raise ReferenciaIndisponivel(f"Metadado ausente na referência D-TISS: {chave}.")
    return str(row["valor"])


def semestres() -> list[str]:
    """Retorne os semestres presentes na base D-TISS."""
    return [semester for semester in _meta("semestres").split(",") if semester]


def fonte() -> str:
    """Retorne a fonte da referência D-TISS."""
    return _meta("fonte")


def atualizado_em() -> str:
    """Retorne a data de atualização da referência D-TISS."""
    return _meta("atualizado_em")


def aviso(semestre: str) -> str | None:
    """Retorne o aviso de qualidade do semestre, se houver."""
    return _aviso(semestre)


def _aviso(semestre: str) -> str | None:
    return (
        "A ANS informa valores atípicos em VL_ITEM_EVENTO_INFORMADO em 2025; os itens acima "
        "de Q3 + 3×IQR de cada célula foram excluídos e a fração excluída é publicada."
        if semestre.startswith("2025-")
        else None
    )


def _normalizar(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold().strip())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _dimensoes(coluna: str, uf: str) -> list[str]:
    try:
        rows = (
            _banco()
            .execute(
                f"SELECT DISTINCT {coluna} AS valor FROM celula WHERE uf = ? AND {coluna} != '' "
                f"ORDER BY {coluna}",
                (uf,),
            )
            .fetchall()
        )
    except sqlite3.Error as exc:
        raise ReferenciaIndisponivel("Não foi possível consultar a referência D-TISS.") from exc
    return [str(row["valor"]) for row in rows]


def _escolher_dimensao(valor: str | None, coluna: str, uf: str) -> str:
    if valor is None:
        return ""
    choices = _dimensoes(coluna, uf)
    normalized = _normalizar(valor)
    for choice in choices:
        if _normalizar(choice) == normalized:
            return choice
    valid = ", ".join(choices)
    raise ValueError(f"{coluna} desconhecido: {valor}. Valores válidos: {valid or 'nenhum'}.")


def valor(
    codigo: str,
    *,
    uf: str,
    tabela: str = "22",
    modalidade: str | None = None,
    porte: str | None = None,
    semestre: str | None = None,
) -> dict[str, Any] | None:
    """Retorne referência D-TISS; pago é só o pago direto ao fornecedor."""
    if not isinstance(codigo, str) or not re.fullmatch(r"[0-9]{1,10}", codigo):
        raise ValueError("codigo deve conter de 1 a 10 dígitos.")
    if not isinstance(uf, str) or uf.upper() not in _UFS:
        raise ValueError("uf deve ser uma UF brasileira válida.")
    uf = uf.upper()
    if not isinstance(tabela, str) or not re.fullmatch(r"[0-9]{2}", tabela):
        raise ValueError("tabela deve conter exatamente 2 dígitos.")
    selected_modality = _escolher_dimensao(modalidade, "modalidade", uf)
    selected_size = _escolher_dimensao(porte, "porte", uf)
    available = semestres()
    selected_semester = semestre if semestre is not None else (available[-1] if available else "")
    if selected_semester not in available:
        raise ValueError(
            f"Semestre desconhecido: {selected_semester}. "
            f"Semestres disponíveis: {', '.join(available) or 'nenhum'}."
        )
    try:
        row = (
            _banco()
            .execute(
                """
            SELECT n, pacote_pct, inf_mediana, inf_p25, inf_p75, inf_excluidos_pct,
                   pago_n, pago_mediana, pago_p25, pago_p75, pago_excluidos_pct
            FROM celula
            WHERE codigo = ? AND tabela = ? AND uf = ? AND modalidade = ?
              AND porte = ? AND semestre = ?
            """,
                (codigo, tabela, uf, selected_modality, selected_size, selected_semester),
            )
            .fetchone()
        )
    except sqlite3.Error as exc:
        raise ReferenciaIndisponivel("Não foi possível consultar a referência D-TISS.") from exc
    if row is None:
        return None
    paid = None
    if row["pago_n"] is not None:
        paid = {
            "descricao": (
                "pago diretamente ao fornecedor (ANS); não é o valor total pago pela operadora"
            ),
            "n": row["pago_n"],
            "mediana": row["pago_mediana"],
            "p25": row["pago_p25"],
            "p75": row["pago_p75"],
            "excluidos_pct": row["pago_excluidos_pct"],
        }
    return {
        "codigo": codigo,
        "tabela": tabela,
        "uf": uf,
        "modalidade": selected_modality or None,
        "porte": selected_size or None,
        "semestre": selected_semester,
        "n": row["n"],
        "pacote_pct": row["pacote_pct"],
        "unidade": "valor unitário em R$ (valor do item ÷ quantidade)",
        "valor_unitario_informado": {
            "mediana": row["inf_mediana"],
            "p25": row["inf_p25"],
            "p75": row["inf_p75"],
            "excluidos_pct": row["inf_excluidos_pct"],
        },
        "valor_unitario_pago_fornecedor": paid,
        "fonte": fonte(),
        "atualizado_em": atualizado_em(),
        "aviso": _aviso(selected_semester),
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Baixe e verifique a referência D-TISS.")
    parser.add_argument("destino", type=Path)
    destination = parser.parse_args(argv).destino
    baixar_verificado(destination, _manifesto(), ReferenciaIndisponivel, "referencia D-TISS")
    return 0


__all__ = [
    "ReferenciaIndisponivel",
    "atualizado_em",
    "aviso",
    "fonte",
    "semestres",
    "valor",
]
