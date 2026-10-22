"""Modelo de chat roteirizado que percorre o fluxo sem chamar um LLM."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from .ferramentas import extrair_codigo_glosa

_CLASSES_POR_GRUPO = {"10": "elegibilidade", "18": "autorizacao", "32": "cobranca"}


def _resultados(mensagens: Sequence[BaseMessage]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (str(m.name), json.loads(str(m.content))) for m in mensagens if isinstance(m, ToolMessage)
    ]


def _chamadas(*chamadas: tuple[str, dict[str, Any]], inicio: int) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": nome, "args": args, "id": f"chamada-{inicio + i}", "type": "tool_call"}
            for i, (nome, args) in enumerate(chamadas)
        ],
    )


def _resumo(resultados: list[tuple[str, dict[str, Any]]]) -> str:
    recursos = [r for n, r in resultados if n == "rascunhar_recurso" and r.get("registrado")]
    envio: dict[str, Any] = next(
        (r for n, r in reversed(resultados) if n == "tiss_sandbox_enviar_lote"), {}
    )
    return (
        f"Lote {envio.get('numero_lote')} aceito no protocolo {envio.get('numero_protocolo')}. "
        f"{len(recursos)} recurso(s) rascunhado(s), com evidência clínica pendente."
        if envio.get("aceito")
        else "O lote não foi aceito."
    )


def _recursos(resultados: list[tuple[str, dict[str, Any]]], inicio: int) -> AIMessage:
    decisoes = next(r for n, r in reversed(resultados) if n == "tiss_parse_demonstrativo")
    grupos = {
        r["codigo"]: r.get("grupo") for n, r in resultados if n == "glosa_explain" and "codigo" in r
    }
    chamadas = []
    for decisao in decisoes["decisoes"]:
        if decisao["decision"] == "pago":
            continue
        codigo = extrair_codigo_glosa(decisao)
        classe = _CLASSES_POR_GRUPO.get(str(grupos.get(codigo)), "outra")
        justificativa = f"Solicitamos a revisão da glosa {codigo} da guia {decisao['guia_ref']}."
        chamadas.append(
            (
                "rascunhar_recurso",
                {
                    "guia": decisao["guia_ref"],
                    "codigo_glosa": codigo,
                    "classe": classe,
                    "justificativa": justificativa,
                },
            )
        )
    return _chamadas(*chamadas, inicio=inicio)


class ModeloRoteirizado(BaseChatModel):
    """Emite as tool calls do fluxo a partir dos resultados já recebidos."""

    cenario: str = "carteirinha_vencida"

    @property
    def _llm_type(self) -> str:
        return "roteirizado"

    def bind_tools(self, tools: Any, **_kwargs: Any) -> ModeloRoteirizado:
        """Ignore as tools: o roteiro já conhece o fluxo."""
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        *_args: Any,
        **_kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._proximo(messages))])

    def _proximo(self, mensagens: Sequence[BaseMessage]) -> AIMessage:
        resultados = _resultados(mensagens)
        inicio = len(resultados)
        if not resultados:
            return _chamadas(("ler_atendimentos", {}), inicio=inicio)
        nome, ultimo = resultados[-1]
        lote = next(r["lote"] for _, r in reversed(resultados) if "lote" in r)
        if nome in {"ler_atendimentos", "tiss_apply_fixes"}:
            return _chamadas(("tiss_validate", {"lote": lote}), inicio=inicio)
        if nome == "tiss_validate" and ultimo.get("valid"):
            return _chamadas(("tiss_build", {"lote": lote}), inicio=inicio)
        if nome == "tiss_validate" and any(a.get("fix") for a in ultimo.get("findings", [])):
            argumentos = {"lote": lote, "report": ultimo["artefato"]}
            return _chamadas(("tiss_apply_fixes", argumentos), inicio=inicio)
        if nome == "tiss_build":
            argumentos = {"xml": ultimo["xml"], "cenario": self.cenario}
            return _chamadas(("tiss_sandbox_enviar_lote", argumentos), inicio=inicio)
        if nome == "tiss_sandbox_enviar_lote" and ultimo.get("aceito"):
            argumentos = {"protocolo": ultimo["protocolo"]}
            return _chamadas(("tiss_sandbox_demonstrativo", argumentos), inicio=inicio)
        if nome == "tiss_sandbox_demonstrativo":
            return _chamadas(("tiss_parse_demonstrativo", {"xml": ultimo["xml"]}), inicio=inicio)
        if nome == "tiss_parse_demonstrativo":
            codigos = sorted(
                {extrair_codigo_glosa(d) for d in ultimo["decisoes"] if d["decision"] != "pago"}
            )
            if codigos:
                chamadas = [("glosa_explain", {"codigo": c}) for c in codigos]
                return _chamadas(*chamadas, inicio=inicio)
        if nome == "glosa_explain":
            return _recursos(resultados, inicio)
        return AIMessage(content=_resumo(resultados))
