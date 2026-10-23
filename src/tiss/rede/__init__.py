"""Consulta a rede hospitalar das operadoras."""

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

from tiss import operadoras
from tiss._dados_remotos import (
    DadosIndisponiveis,
    baixar_verificado,
    caminho_cache,
    validar_manifesto,
)
from tiss._dados_remotos import (
    conectar as conectar_remoto,
)
from tiss._dados_remotos import (
    sha256 as sha256_remoto,
)

_MANIFEST_PATH = Path(__file__).parent / "_data" / "manifesto.json"


class RedeIndisponivel(DadosIndisponiveis):
    """Indica que os dados da rede não puderam ser verificados ou lidos."""

    codigo = "rede_indisponivel"


def _ler_manifesto() -> dict[str, Any]:
    try:
        manifesto = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RedeIndisponivel("O manifesto da rede hospitalar não está disponível.") from exc
    if not isinstance(manifesto, dict):
        raise RedeIndisponivel("O manifesto da rede hospitalar é inválido.")
    return cast(dict[str, Any], manifesto)


def _validar_manifesto(manifesto: dict[str, Any]) -> None:
    validar_manifesto(manifesto, RedeIndisponivel)


def _sha256(path: Path) -> tuple[str, int]:
    return sha256_remoto(path)


def _baixar_verificado(destino: Path, manifesto: dict[str, Any]) -> Path:
    return baixar_verificado(destino, manifesto, RedeIndisponivel, "rede")


def _caminho_banco() -> Path:
    configurado = os.environ.get("TISS_REDE")
    if configurado:
        caminho = Path(configurado).expanduser().resolve()
        if not caminho.is_file():
            raise RedeIndisponivel(f"Arquivo SQLite da rede não encontrado: {caminho}")
        return caminho

    manifesto = _ler_manifesto()
    _validar_manifesto(manifesto)
    caminho, valido = caminho_cache(f"rede-{manifesto['sqlite_sha256'][:16]}", manifesto)
    if valido:
        return caminho
    return _baixar_verificado(caminho, manifesto)


@cache
def _conectar(caminho: str) -> sqlite3.Connection:
    try:
        return conectar_remoto(caminho, RedeIndisponivel, "rede hospitalar")
    except sqlite3.Error as exc:
        raise RedeIndisponivel("O banco SQLite da rede não pôde ser aberto.") from exc


def _banco() -> sqlite3.Connection:
    return _conectar(str(_caminho_banco()))


def _cnpj_valido(cnpj: str) -> bool:
    if not re.fullmatch(r"[0-9]{14}", cnpj) or len(set(cnpj)) == 1:
        return False
    for tamanho, pesos in (
        (12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
        (13, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
    ):
        soma = sum(int(digito) * peso for digito, peso in zip(cnpj[:tamanho], pesos, strict=True))
        resto = soma % 11
        verificador = 0 if resto < 2 else 11 - resto
        if int(cnpj[tamanho]) != verificador:
            return False
    return True


def _normalizar_registro(registro_ans: str) -> str:
    if not isinstance(registro_ans, str):
        raise ValueError("registro_ans deve conter 5 ou 6 dígitos.")
    registro = registro_ans.strip()
    if not registro.isdigit() or len(registro) not in {5, 6}:
        raise ValueError("registro_ans deve conter 5 ou 6 dígitos.")
    cadastro = operadoras.lookup(registro)
    return str(cadastro["registro_ans"]) if cadastro else registro.zfill(6)


def _lista(valor: str) -> list[str]:
    return valor.split("|") if valor else []


def operadoras_do_estabelecimento(
    cnpj: str | None = None, cnes: str | None = None
) -> list[dict[str, Any]]:
    """Liste as operadoras vinculadas a um CNPJ ou CNES."""
    if (cnpj is None) == (cnes is None):
        raise ValueError("Informe exatamente um entre cnpj e cnes.")
    if cnpj is not None:
        if not isinstance(cnpj, str):
            raise ValueError("CNPJ inválido.")
        identificador = "".join(
            digito for digito in cnpj.strip() if not unicodedata.category(digito).startswith("P")
        )
        if not _cnpj_valido(identificador):
            raise ValueError("CNPJ inválido.")
        coluna = "e.cnpj"
    else:
        if not isinstance(cnes, str):
            raise ValueError("CNES inválido.")
        identificador = cnes.strip()
        if not re.fullmatch(r"[0-9]{7}", identificador) or identificador == "0000000":
            raise ValueError("CNES deve conter 7 dígitos diferentes de zero.")
        coluna = "e.cnes"
    try:
        linhas = (
            _banco()
            .execute(
                f"""
            SELECT v.registro_ans, e.cnes, e.nome AS nome_estabelecimento,
                   v.tipo_contrato, v.disponibilidade, v.tipo_prestador,
                   v.urgencia_emergencia, v.dt_vinculo_inicio, v.planos
            FROM estabelecimento AS e
            JOIN vinculo AS v ON v.estabelecimento = e.id
            WHERE {coluna} = ?
            ORDER BY v.registro_ans, e.cnes
            """,
                (identificador,),
            )
            .fetchall()
        )
    except sqlite3.Error as exc:
        raise RedeIndisponivel("Não foi possível consultar a rede hospitalar.") from exc
    nomes: dict[str, str | None] = {}
    resultado = []
    for linha in linhas:
        registro = linha["registro_ans"]
        if registro not in nomes:
            cadastro = operadoras.lookup(registro)
            nomes[registro] = cadastro.get("razao_social") if cadastro else None
        resultado.append(
            {
                "registro_ans": registro,
                "nome": nomes[registro],
                "cnes": linha["cnes"],
                "nome_estabelecimento": linha["nome_estabelecimento"],
                "tipo_contrato": _lista(linha["tipo_contrato"]),
                "disponibilidade": _lista(linha["disponibilidade"]),
                "tipo_prestador": _lista(linha["tipo_prestador"]),
                "urgencia_emergencia": bool(linha["urgencia_emergencia"]),
                "dt_vinculo_inicio": linha["dt_vinculo_inicio"],
                "planos": linha["planos"],
            }
        )
    return resultado


def estabelecimentos_da_operadora(registro_ans: str, uf: str | None = None) -> list[dict[str, Any]]:
    """Liste os estabelecimentos vinculados a uma operadora."""
    registro = _normalizar_registro(registro_ans)
    if uf is not None:
        if not isinstance(uf, str) or not re.fullmatch(r"[A-Za-z]{2}", uf.strip()):
            raise ValueError("UF deve conter duas letras.")
        uf = uf.strip().upper()
    filtro_uf = " AND e.uf = ?" if uf else ""
    parametros = (registro, uf) if uf else (registro,)
    try:
        linhas = (
            _banco()
            .execute(
                f"""
            SELECT e.id, e.cnes, e.cnpj, e.nome, e.classe, e.cd_municipio, e.uf,
                   v.tipo_contrato, v.disponibilidade, v.tipo_prestador,
                   v.urgencia_emergencia, v.dt_vinculo_inicio, v.planos
            FROM estabelecimento AS e
            JOIN vinculo AS v ON v.estabelecimento = e.id
            WHERE v.registro_ans = ?{filtro_uf}
            ORDER BY e.uf, e.nome, e.cnes
            """,
                parametros,
            )
            .fetchall()
        )
    except sqlite3.Error as exc:
        raise RedeIndisponivel("Não foi possível consultar a rede hospitalar.") from exc
    return [
        {
            **{
                chave: linha[chave]
                for chave in ("cnes", "cnpj", "nome", "classe", "cd_municipio", "uf")
            },
            "tipo_contrato": _lista(linha["tipo_contrato"]),
            "disponibilidade": _lista(linha["disponibilidade"]),
            "tipo_prestador": _lista(linha["tipo_prestador"]),
            "urgencia_emergencia": bool(linha["urgencia_emergencia"]),
            "dt_vinculo_inicio": linha["dt_vinculo_inicio"],
            "planos": linha["planos"],
        }
        for linha in linhas
    ]


def resumo_da_operadora(registro_ans: str) -> dict[str, Any]:
    """Conte os estabelecimentos vinculados à operadora por UF."""
    registro = _normalizar_registro(registro_ans)
    try:
        linhas = (
            _banco()
            .execute(
                """
            SELECT e.uf, COUNT(DISTINCT e.id) AS total
            FROM estabelecimento AS e
            JOIN vinculo AS v ON v.estabelecimento = e.id
            WHERE v.registro_ans = ?
            GROUP BY e.uf
            ORDER BY e.uf
            """,
                (registro,),
            )
            .fetchall()
        )
    except sqlite3.Error as exc:
        raise RedeIndisponivel("Não foi possível consultar a rede hospitalar.") from exc
    por_uf = {linha["uf"]: linha["total"] for linha in linhas}
    return {
        "registro_ans": registro,
        "estabelecimentos": sum(por_uf.values()),
        "por_uf": por_uf,
    }


def _meta(chave: str) -> str:
    try:
        linha = _banco().execute("SELECT valor FROM meta WHERE chave = ?", (chave,)).fetchone()
    except sqlite3.Error as exc:
        raise RedeIndisponivel("Não foi possível consultar os metadados da rede.") from exc
    if linha is None:
        raise RedeIndisponivel(f"Metadado ausente na rede hospitalar: {chave}.")
    return str(linha["valor"])


def atualizado_em() -> str:
    """Retorne a data dos dados da rede."""
    return _meta("atualizado_em")


def fonte() -> str:
    """Retorne a fonte dos dados da rede."""
    return _meta("fonte")


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Baixe e verifique o SQLite da rede hospitalar.")
    parser.add_argument("destino", type=Path)
    destino = parser.parse_args(argv).destino
    _baixar_verificado(destino, _ler_manifesto())
    return 0


__all__ = [
    "RedeIndisponivel",
    "atualizado_em",
    "estabelecimentos_da_operadora",
    "fonte",
    "operadoras_do_estabelecimento",
    "resumo_da_operadora",
]
