"""Ferramentas do agente: tools do MCP voa-tiss com artefatos e passos locais."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from mcp.types import Tool

from .planilha import ler_lote

FERRAMENTAS_MCP = (
    "tiss_validate",
    "tiss_apply_fixes",
    "tiss_build",
    "tiss_sandbox_enviar_lote",
    "tiss_sandbox_demonstrativo",
    "tiss_parse_demonstrativo",
    "glosa_explain",
)
RECURSO_URL = "https://tiss-api.voa.health/recurso"
CLASSES = ("elegibilidade", "autorizacao", "cobranca", "tecnica", "outra")
_CAMPOS_ARTEFATO = ("xml", "lote", "protocolo", "resumo")
_ENTRADAS_ARTEFATO = ("xml", "lote", "protocolo", "report")
_REFERENCIA = re.compile(r"^artefato:(\d+)(?:\.(\w+))?$")
_GLOSADO = ("glosado", "glosa_parcial")

Chamada = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class Execucao:
    """Estado de uma execução: artefatos, histórico de tools e recursos."""

    arquivo: Path
    chamar: Chamada
    relatar: Callable[[str], None] = lambda _texto: None
    max_rodadas: int = 3
    artefatos: list[Any] = field(default_factory=list)
    historico: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    recursos: list[dict[str, Any]] = field(default_factory=list)
    rodadas: int = 0

    def guardar(self, nome: str, resultado: dict[str, Any]) -> str:
        """Guarde o resultado e devolva a visão compacta para o modelo."""
        self.historico.append((nome, resultado))
        self.artefatos.append(resultado)
        referencia = f"artefato:{len(self.artefatos)}"
        visao: dict[str, Any] = {"artefato": referencia}
        for chave, valor in resultado.items():
            grande = chave in _CAMPOS_ARTEFATO and valor is not None
            visao[chave] = f"{referencia}.{chave}" if grande else valor
        texto = json.dumps(visao, ensure_ascii=False)
        self.relatar(f"  ← {_curto(texto)}")
        return texto

    def resolver(self, valor: Any) -> Any:
        """Troque referências artefato:N[.campo] pelos valores guardados."""
        if isinstance(valor, dict):
            return {chave: self.resolver(item) for chave, item in valor.items()}
        if isinstance(valor, list):
            return [self.resolver(item) for item in valor]
        if isinstance(valor, str) and (achado := _REFERENCIA.match(valor)):
            indice = int(achado.group(1)) - 1
            if not 0 <= indice < len(self.artefatos):
                raise ValueError(f"Artefato inexistente: {valor}")
            guardado = self.artefatos[indice]
            return copy.deepcopy(guardado[achado.group(2)] if achado.group(2) else guardado)
        return valor

    def ultimo(self, nome: str) -> dict[str, Any] | None:
        """Devolva o último resultado de uma tool."""
        return next((r for n, r in reversed(self.historico) if n == nome), None)

    def glosas(self) -> list[dict[str, Any]]:
        """Liste as decisões glosadas do último demonstrativo lido."""
        lido = self.ultimo("tiss_parse_demonstrativo") or {}
        return [d for d in lido.get("decisoes", []) if d.get("decision") in _GLOSADO]

    def resultado(self, resumo: str) -> dict[str, Any]:
        """Monte a saída estruturada a partir do que as tools devolveram."""
        envio = self.ultimo("tiss_sandbox_enviar_lote") or {}
        validacao = self.ultimo("tiss_validate") or {}
        explicacoes = {
            r["codigo"]: r for n, r in self.historico if n == "glosa_explain" and "codigo" in r
        }
        recursos = {(r["guia"], r["codigo_glosa"]): r for r in self.recursos}
        glosas = []
        for decisao in self.glosas():
            codigo = extrair_codigo_glosa(decisao)
            explicacao = explicacoes.get(codigo, {})
            glosas.append(
                {
                    "guia": decisao["guia_ref"],
                    "codigo": codigo,
                    "descricao": explicacao.get("descricao"),
                    "grupo": explicacao.get("grupo"),
                    "valor_glosa_cents": decisao.get("valor_glosa_cents"),
                    "recurso": (decisao["guia_ref"], codigo) in recursos,
                }
            )
        aceito = bool(envio.get("aceito"))
        concluido = aceito and all(glosa["recurso"] for glosa in glosas)
        return {
            "status": "concluido" if concluido else "incompleto",
            "lote": {
                "numero_lote": envio.get("numero_lote"),
                "aceito": aceito,
                "numero_protocolo": envio.get("numero_protocolo"),
                "cenario": envio.get("cenario"),
                "rodadas_de_correcao": self.rodadas,
                "valido": bool(validacao.get("valid")),
            },
            "glosas": glosas,
            "recursos": sorted(self.recursos, key=lambda r: (r["guia"], r["codigo_glosa"])),
            "resumo": resumo,
        }


def extrair_codigo_glosa(decisao: dict[str, Any]) -> str:
    """Extraia o código de glosa do motivo devolvido pelo demonstrativo."""
    return str(decisao.get("motivo", "")).split(";")[0].split(" ")[0].strip()


def _curto(texto: str, limite: int = 110) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def _esquema(tool: Tool) -> dict[str, Any]:
    esquema = copy.deepcopy(tool.inputSchema)
    esquema.pop("oneOf", None)
    for nome in _ENTRADAS_ARTEFATO:
        if nome in esquema.get("properties", {}):
            esquema["properties"][nome] = {
                "type": "string",
                "description": "Referência artefato:N ou artefato:N.campo de uma tool anterior.",
            }
    return esquema


def _ferramenta_mcp(execucao: Execucao, tool: Tool) -> BaseTool:
    async def executar(**argumentos: Any) -> str:
        execucao.relatar(f"→ {tool.name} {_curto(json.dumps(argumentos, ensure_ascii=False))}")
        if tool.name == "tiss_apply_fixes":
            if execucao.rodadas >= execucao.max_rodadas:
                erro = {"codigo": "limite_de_rodadas", "mensagem": "Limite de correções atingido."}
                return execucao.guardar(tool.name, {"erro": erro})
            execucao.rodadas += 1
        try:
            resolvidos = execucao.resolver(argumentos)
        except (ValueError, KeyError, TypeError) as exc:
            return execucao.guardar(
                tool.name, {"erro": {"codigo": "artefato", "mensagem": str(exc)}}
            )
        return execucao.guardar(tool.name, await execucao.chamar(tool.name, resolvidos))

    return StructuredTool.from_function(
        coroutine=executar,
        name=tool.name,
        description=tool.description or tool.name,
        args_schema=_esquema(tool),
    )


def _ferramentas_locais(execucao: Execucao) -> list[BaseTool]:
    async def ler_atendimentos() -> str:
        execucao.relatar(f"→ ler_atendimentos {execucao.arquivo.name}")
        lote = ler_lote(execucao.arquivo)
        itens = sum(len(g.get("procedimentos_executados", [])) for g in lote["guias"])
        return execucao.guardar(
            "ler_atendimentos", {"lote": lote, "guias": len(lote["guias"]), "itens": itens}
        )

    async def rascunhar_recurso(
        guia: str, codigo_glosa: str, classe: str, justificativa: str
    ) -> str:
        execucao.relatar(f"→ rascunhar_recurso guia={guia} glosa={codigo_glosa} classe={classe}")
        glosadas = {(d["guia_ref"], extrair_codigo_glosa(d)) for d in execucao.glosas()}
        if (guia, codigo_glosa) not in glosadas or classe not in CLASSES:
            erro = {"codigo": "recurso_invalido", "mensagem": "Guia, glosa ou classe inexistente."}
            return execucao.guardar("rascunhar_recurso", {"erro": erro})
        recurso = {
            "guia": guia,
            "codigo_glosa": codigo_glosa,
            "classe": classe,
            "justificativa": justificativa,
            "needs": ["evidencia_clinica"],
            "cta": {"texto": "Recurso com evidência clínica", "url": RECURSO_URL},
        }
        execucao.recursos.append(recurso)
        return execucao.guardar("rascunhar_recurso", {"registrado": True, **recurso})

    return [
        StructuredTool.from_function(
            coroutine=ler_atendimentos,
            name="ler_atendimentos",
            description="Lê a planilha de atendimentos e devolve o lote TISS em JSON.",
        ),
        StructuredTool.from_function(
            coroutine=rascunhar_recurso,
            name="rascunhar_recurso",
            description=(
                "Registra o rascunho de recurso de uma glosa. A evidência clínica fica "
                f"pendente em needs. classe: {', '.join(CLASSES)}."
            ),
        ),
    ]


def criar_ferramentas(execucao: Execucao, tools: list[Tool]) -> list[BaseTool]:
    """Crie as tools do agente a partir das tools do MCP."""
    mcp = [_ferramenta_mcp(execucao, tool) for tool in tools if tool.name in FERRAMENTAS_MCP]
    faltando = set(FERRAMENTAS_MCP) - {tool.name for tool in mcp}
    if faltando:
        raise RuntimeError(f"Servidor MCP sem as tools: {', '.join(sorted(faltando))}")
    return [*_ferramentas_locais(execucao), *mcp]
