"""Preparação do Painel de Indicadores de Glosa da ANS."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

if __package__:
    from ._manutencao_common import download, read_csv, sha256
else:
    from _manutencao_common import download, read_csv, sha256

ROOT = Path(__file__).resolve().parents[1]
INDICADORES_OUT = ROOT / "src/voa_tiss/operadoras/_data/indicadores.json"
CADOP = ROOT / "src/voa_tiss/operadoras/_data/healthplans.json"
PAINEL_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/painel_de_glosas-057/dados/"
PAINEL_PAGINA = "https://dados.gov.br/dados/conjuntos-dados/painel-de-indicadores-de-glosa"
PAINEL_ARQUIVOS = {
    "glosa_inicial": ("percentual_glosa_inicial", "PC_GLOSA_INCIAL"),
    "glosa_final": ("percentual_glosa_final", "PC_GLOSA_FINAL"),
    "tempo_medio_pagamento": ("tempo_medio_pagamento", "QT_TEMPO_PAGAMENTO"),
    "guias_sem_retorno": ("numero_guias_sem_retorno", "PC_NUMERO_GUIAS_SEM_RETORNO"),
    "valor_guias_sem_retorno": ("valor_guias_sem_retorno", "PC_VALOR_GUIAS_SEM_RETORNO"),
}
LIMITE_MEDIANA = 3
# Em séries baixas, três vezes a mediana é pouco; o salto mínimo ignora a oscilação.
SALTO_MINIMO = {"tempo_medio_pagamento": 30}
SALTO_MINIMO_PADRAO = 10


def _valor(raw: str) -> float | None:
    text = raw.strip()
    # A ANS marca dado inconsistente com "-"; o CSV também publica a célula vazia.
    if text in {"", "-"}:
        return None
    return float(text.replace(",", "."))


def _salto(chave: str, valor: float, anteriores: list[float]) -> bool:
    mediana = statistics.median(anteriores)
    minimo = SALTO_MINIMO.get(chave, SALTO_MINIMO_PADRAO)
    return valor > LIMITE_MEDIANA * mediana and valor - mediana >= minimo


def _inconsistentes(serie: list[dict[str, Any]]) -> None:
    for chave in PAINEL_ARQUIVOS:
        anteriores: list[float] = []
        for linha in serie:
            if chave not in linha:
                continue
            valor = linha[chave]
            if valor is None or (anteriores and _salto(chave, valor, anteriores)):
                linha["inconsistentes"].append(chave)
            if valor is not None:
                anteriores.append(valor)


def _arquivo(nome: str) -> str:
    return f"pda-057-painel_de_glosas-{nome}.csv"


def baixar_painel(destino: Path) -> None:
    """Baixe os CSVs do painel."""
    for nome, _ in PAINEL_ARQUIVOS.values():
        download(PAINEL_URL + _arquivo(nome), destino / _arquivo(nome))


def bake_painel(origem: Path) -> dict[str, Any]:
    """Gere a série semestral por operadora ativa no CADOP."""
    ativas = set(json.loads(CADOP.read_text(encoding="utf-8"))["records"])
    series: dict[str, dict[str, dict[str, Any]]] = {}
    cargas = set()
    arquivos = []
    for chave, (nome, coluna) in PAINEL_ARQUIVOS.items():
        path = origem / _arquivo(nome)
        arquivos.append({"url": PAINEL_URL + _arquivo(nome), "sha256": sha256(path)})
        for row in read_csv(path):
            registro = row["REGISTRO_OPERADORA"].strip()
            if registro not in ativas:
                continue
            periodo = row["CD_PERIODO"].strip()
            linha = series.setdefault(registro, {}).setdefault(
                periodo, {"periodo": periodo, "inconsistentes": []}
            )
            linha[chave] = _valor(row[coluna])
            cargas.add(row["DT_CARGA"].strip())
    records = {}
    for registro in sorted(series):
        serie = [series[registro][periodo] for periodo in sorted(series[registro])]
        _inconsistentes(serie)
        records[registro] = [
            [
                linha["periodo"],
                *(linha.get(chave) for chave in PAINEL_ARQUIVOS),
                linha["inconsistentes"],
            ]
            for linha in serie
        ]
    return {
        "version": 1,
        "fonte": {
            "titulo": "ANS, Painel de Indicadores de Glosa",
            "url": PAINEL_PAGINA,
            "licenca": "CC BY",
            "atualizado_em": max(cargas),
            "arquivos": arquivos,
        },
        "colunas": ["periodo", *PAINEL_ARQUIVOS, "inconsistentes"],
        "records": records,
    }


def write_painel(path: Path, data: dict[str, Any]) -> None:
    """Grave o JSON com uma operadora por linha, para diffs legíveis."""
    head = {key: value for key, value in data.items() if key != "records"}
    rows = ",\n".join(
        f"    {json.dumps(registro)}: {json.dumps(serie, separators=(',', ':'))}"
        for registro, serie in data["records"].items()
    )
    text = json.dumps(head, ensure_ascii=False, indent=2, sort_keys=True)[:-2]
    path.write_text(f'{text},\n  "records": {{\n{rows}\n  }}\n}}\n', encoding="utf-8", newline="\n")
