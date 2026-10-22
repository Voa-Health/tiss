"""Fluxo completo contra a operadora simulada local com modelo roteirizado."""

from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path

import pytest
from faturista.__main__ import EXEMPLO, legivel
from faturista.fluxo import executar, servidor_local
from faturista.planilha import ler_lote
from faturista.roteiro import ModeloRoteirizado
from openpyxl import Workbook


def _entrada(formato: str, pasta: Path) -> Path:
    if formato == "csv":
        return EXEMPLO
    with EXEMPLO.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.reader(arquivo))
    destino = pasta / f"atendimentos.{formato}"
    if formato == "json":
        destino.write_text(json.dumps(ler_lote(EXEMPLO)), encoding="utf-8")
    else:
        planilha = Workbook()
        for linha in linhas:
            planilha.active.append(linha)
        planilha.save(destino)
    return destino


@pytest.mark.parametrize(
    ("formato", "cenario", "glosas"),
    [
        ("csv", "carteirinha_vencida", {("0001", "1017"), ("0002", "1017"), ("0003", "1017")}),
        ("xlsx", "sem_autorizacao", {("0001", "1402")}),
        ("json", "aprovado", set()),
    ],
)
def test_fluxo_fecha_o_ciclo(
    formato: str, cenario: str, glosas: set[tuple[str, str]], tmp_path: Path
) -> None:
    arquivo = _entrada(formato, tmp_path)
    with servidor_local() as url:
        resultado = asyncio.run(
            executar(arquivo, ModeloRoteirizado(cenario=cenario), url=url, cenario=cenario)
        )
    lote = resultado["lote"]
    assert (resultado["status"], lote["aceito"], lote["valido"]) == ("concluido", True, True)
    assert lote["numero_protocolo"] and lote["rodadas_de_correcao"] == 1
    assert {(g["guia"], g["codigo"]) for g in resultado["glosas"]} == glosas
    assert {(r["guia"], r["codigo_glosa"]) for r in resultado["recursos"]} == glosas
    for recurso in resultado["recursos"]:
        assert recurso["needs"] == ["evidencia_clinica"]
        assert recurso["cta"]["url"] == "https://tiss-api.voa.health/recurso"
    assert "aceito" in resultado["resumo"] and lote["numero_lote"] in legivel(resultado)
