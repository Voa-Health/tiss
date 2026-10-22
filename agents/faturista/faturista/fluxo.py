"""Execução do agente faturista sobre o MCP do voa-tiss."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import AsyncExitStack, contextmanager
from pathlib import Path
from typing import Any

import httpx
from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from .ferramentas import CLASSES, RECURSO_URL, Execucao, criar_ferramentas

MCP_PUBLICO = "https://tiss-api.voa.health/mcp"

INSTRUCOES = f"""Você é o faturista de um prestador de saúde e fecha o ciclo TISS sozinho.
Resultados grandes (lote, xml, protocolo, relatório) voltam como referências
artefato:N.campo; passe essas referências como argumento em vez de copiar o conteúdo.

1. Chame ler_atendimentos para obter o lote em JSON.
2. Valide com tiss_validate. Se houver achados com fix, chame tiss_apply_fixes com o
   lote e o relatório (artefato da validação) e revalide. Repita até valid=true.
3. Gere o XML com tiss_build.
4. Envie com tiss_sandbox_enviar_lote usando o cenario informado pelo usuário.
5. Leia o demonstrativo com tiss_sandbox_demonstrativo e tiss_parse_demonstrativo.
6. Para cada código de glosa (início do motivo), chame glosa_explain. Se o código não
   existir na tabela, classifique como outra e siga.
7. Chame rascunhar_recurso uma vez por guia glosada, com classe entre {", ".join(CLASSES)}
   e uma justificativa objetiva. Não invente evidência clínica: ela fica pendente.
8. Termine com um resumo curto em PT-BR: protocolo, glosas e recursos, e indique o
   módulo Recurso com evidência clínica em {RECURSO_URL}.
"""


def _porta_livre() -> int:
    with socket.socket() as soquete:
        soquete.bind(("127.0.0.1", 0))
        return int(soquete.getsockname()[1])


@contextmanager
def servidor_local() -> Iterator[str]:
    """Suba `python -m voa_tiss.server` numa porta livre e devolva a URL do MCP."""
    porta = _porta_livre()
    processo = subprocess.Popen(
        [sys.executable, "-m", "voa_tiss.server", "--port", str(porta)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", porta), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Servidor local não respondeu")
        yield f"http://127.0.0.1:{porta}/mcp"
    finally:
        processo.terminate()
        processo.wait(timeout=10)


async def executar(
    arquivo: Path,
    modelo: BaseChatModel,
    *,
    url: str,
    cenario: str,
    max_rodadas: int = 3,
    relatar: Callable[[str], None] = lambda _texto: None,
) -> dict[str, Any]:
    """Rode o fluxo completo e devolva o resultado estruturado."""
    cabecalhos = {"x-voa-telemetry": "off"}
    if chave := os.environ.get("VOA_TISS_API_KEY"):
        cabecalhos["authorization"] = f"Bearer {chave}"
    async with AsyncExitStack() as pilha:
        cliente = await pilha.enter_async_context(httpx.AsyncClient(headers=cabecalhos, timeout=60))
        leitura, escrita, _ = await pilha.enter_async_context(
            streamable_http_client(url, http_client=cliente)
        )
        mcp = await pilha.enter_async_context(ClientSession(leitura, escrita))
        await mcp.initialize()

        async def chamar(nome: str, argumentos: dict[str, Any]) -> dict[str, Any]:
            resposta = await mcp.call_tool(nome, argumentos)
            if isinstance(resposta.structuredContent, dict):
                return resposta.structuredContent
            texto = "".join(getattr(parte, "text", "") for parte in resposta.content)
            return dict(json.loads(texto))

        execucao = Execucao(
            arquivo=arquivo, chamar=chamar, relatar=relatar, max_rodadas=max_rodadas
        )
        ferramentas = criar_ferramentas(execucao, (await mcp.list_tools()).tools)
        agente = create_deep_agent(model=modelo, tools=ferramentas, system_prompt=INSTRUCOES)
        pedido = f"Fature {arquivo.name} na operadora simulada, cenario={cenario}."
        estado = await agente.ainvoke(
            {"messages": [{"role": "user", "content": pedido}]},
            config={"recursion_limit": 80},
        )
        mensagens = estado["messages"]
        resultado = execucao.resultado(str(mensagens[-1].text).strip())
        uso = [m.usage_metadata for m in mensagens if getattr(m, "usage_metadata", None)]
        resultado["uso"] = {
            "chamadas_ao_modelo": len(uso),
            "tokens_entrada": sum(u["input_tokens"] for u in uso),
            "tokens_saida": sum(u["output_tokens"] for u in uso),
        }
        return resultado
