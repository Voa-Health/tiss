"""Avaliação de descoberta do tiss em respostas de modelos via OpenRouter."""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "evals/descoberta/prompts.yaml"
RESULTADOS = ROOT / "evals/descoberta/resultados"
API = "https://openrouter.ai/api/v1/chat/completions"
TERMOS = re.compile(
    r"tiss-api\.voa\.health|voa-health/tiss|pypi\.org/project/tiss\b|"
    r"pip install \"?tiss\b|import tiss\b|from tiss import",
    re.IGNORECASE,
)


class _Orcamento:
    """Reserva o teto por chamada e soma o custo reportado."""

    def __init__(self, limite: float, teto_chamada: float) -> None:
        self.limite = limite
        self.teto_chamada = teto_chamada
        self.gasto = 0.0
        self.reservado = 0.0
        self._lock = Lock()

    def reservar(self) -> bool:
        with self._lock:
            if self.gasto + self.reservado + self.teto_chamada > self.limite:
                return False
            self.reservado += self.teto_chamada
            return True

    def liquidar(self, valor: float) -> None:
        with self._lock:
            self.reservado -= self.teto_chamada
            self.gasto += valor


def _termos(texto: str) -> list[str]:
    return sorted({match.lower() for match in TERMOS.findall(texto)})


def _perguntar(
    chave: str, modelo: dict[str, str], texto: str, config: dict[str, Any]
) -> dict[str, Any]:
    corpo: dict[str, Any] = {
        "model": modelo["slug"],
        "messages": [{"role": "user", "content": texto}],
        "temperature": config["temperatura"],
        "max_tokens": config["max_tokens"],
        "usage": {"include": True},
    }
    if config["busca_web"] and modelo.get("motor_busca"):
        corpo["plugins"] = [{"id": "web", "engine": modelo["motor_busca"]}]
    elif config["busca_web"]:
        corpo["model"] = f"{modelo['slug']}:online"
    request = urllib.request.Request(
        API,
        data=json.dumps(corpo).encode(),
        headers={
            "Authorization": f"Bearer {chave}",
            "Content-Type": "application/json",
            "X-Title": "tiss descoberta",
        },
    )
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return dict(json.load(response))
        except (urllib.error.URLError, TimeoutError) as error:
            definitivo = isinstance(error, urllib.error.HTTPError) and error.code < 500
            if definitivo or tentativa == 2:
                raise
            logging.warning("%s: %s; repetindo", modelo["slug"], error)
            time.sleep(5 * (tentativa + 1))
    raise AssertionError


def _item(
    chave: str,
    modelo: dict[str, str],
    prompt: dict[str, str],
    config: dict[str, Any],
    orcamento: _Orcamento,
    brutos: Path | None,
) -> dict[str, Any]:
    item: dict[str, Any] = {"prompt": prompt["id"], "slug": modelo["slug"]}
    if not orcamento.reservar():
        return {**item, "erro": "orçamento esgotado"}
    try:
        resposta = _perguntar(chave, modelo, prompt["texto"], config)
        usage = resposta.get("usage") or {}
        custo = float(usage.get("cost") or 0.0)
    except Exception as error:
        orcamento.liquidar(0.0)
        return {**item, "erro": type(error).__name__}
    orcamento.liquidar(custo)
    mensagem = (resposta.get("choices") or [{}])[0].get("message") or {}
    texto = mensagem.get("content") or ""
    fontes = [
        str(nota.get("url_citation", {}).get("url", ""))
        for nota in mensagem.get("annotations") or []
        if nota.get("type") == "url_citation"
    ]
    if brutos:
        destino = brutos / f"{modelo['slug'].replace('/', '__')}__{prompt['id']}.json"
        destino.write_text(json.dumps(resposta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        **item,
        "modelo_servido": resposta.get("model"),
        "mencao": bool(_termos(texto)),
        "termos": _termos(texto),
        "mencao_fontes": any(_termos(url) for url in fontes),
        "fontes": len(fontes),
        "tokens_saida": usage.get("completion_tokens"),
        "custo_usd": round(custo, 6),
    }


def _resumo(modelos: list[dict[str, str]], itens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    linhas = []
    for modelo in modelos:
        proprios = [item for item in itens if item["slug"] == modelo["slug"]]
        validos = [item for item in proprios if "erro" not in item]
        linhas.append(
            {
                "empresa": modelo["empresa"],
                "slug": modelo["slug"],
                "respostas": len(validos),
                "erros": len(proprios) - len(validos),
                "mencoes": sum(item["mencao"] for item in validos),
                "mencoes_fontes": sum(item["mencao_fontes"] for item in validos),
                "custo_usd": round(sum(item["custo_usd"] for item in validos), 4),
            }
        )
    return linhas


def tabela(resultado: dict[str, Any]) -> str:
    """Formata o resumo de uma rodada como tabela Markdown."""
    linhas = [
        "| Modelo | Slug | Respostas | Citam o tiss | Fontes com o tiss | Custo (US$) |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for linha in resultado["resumo"]:
        linhas.append(
            f"| {linha['empresa']} | `{linha['slug']}` | {linha['respostas']} | "
            f"{linha['mencoes']} | {linha['mencoes_fontes']} | {linha['custo_usd']:.4f} |"
        )
    return "\n".join(linhas)


def descoberta(
    limite_usd: float,
    brutos: Path | None = None,
    paralelo: int = 8,
    teto_chamada_usd: float = 0.25,
) -> int:
    """Roda os prompts nos modelos configurados e grava o resultado datado."""
    import yaml

    chave = os.environ.get("OPENROUTER_API_KEY")
    if not chave:
        logging.error("Defina OPENROUTER_API_KEY")
        return 2
    spec = yaml.safe_load(PROMPTS.read_text(encoding="utf-8"))
    modelos, prompts, config = spec["modelos"], spec["prompts"], spec["configuracao"]
    if brutos:
        brutos.mkdir(parents=True, exist_ok=True)
    orcamento = _Orcamento(limite_usd, teto_chamada_usd)
    pares = [(modelo, prompt) for modelo in modelos for prompt in prompts]
    with ThreadPoolExecutor(paralelo) as pool:
        itens = list(
            pool.map(lambda par: _item(chave, par[0], par[1], config, orcamento, brutos), pares)
        )
    data = datetime.now(timezone.utc).date().isoformat()
    resultado = {
        "data": data,
        "configuracao": {
            **config,
            "api": API,
            "sufixo": ":online" if config["busca_web"] else "",
            "ferramentas": [],
            "termos": TERMOS.pattern,
        },
        "modelos": modelos,
        "resumo": _resumo(modelos, itens),
        "custo_total_usd": round(orcamento.gasto, 4),
        "itens": itens,
    }
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    destino = RESULTADOS / f"{data}.json"
    destino.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(tabela(resultado))
    logging.info("%s custo=%.4f USD", destino.relative_to(ROOT), orcamento.gasto)
    return 0 if all("erro" not in item for item in itens) else 1
