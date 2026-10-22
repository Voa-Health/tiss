"""Escolha do modelo de chat por configuração."""

from __future__ import annotations

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from .roteiro import ModeloRoteirizado

OPENROUTER_URL = "https://openrouter.ai/api/v1"
MODELO_PADRAO = "openrouter:anthropic/claude-sonnet-5.5"


def criar_modelo(especificacao: str, *, cenario: str) -> BaseChatModel:
    """Crie o modelo a partir de provedor:nome (openrouter, openai, anthropic, roteirizado)."""
    provedor, _, nome = especificacao.partition(":")
    if provedor == "roteirizado":
        return ModeloRoteirizado(cenario=cenario)
    if provedor == "openrouter":
        return ChatOpenAI(
            model=nome,
            base_url=OPENROUTER_URL,
            api_key=os.environ["OPENROUTER_API_KEY"],  # type: ignore[arg-type]
        )
    if provedor == "openai":
        return ChatOpenAI(model=nome)
    if provedor == "anthropic":
        return ChatAnthropic(model=nome)  # type: ignore[call-arg]
    raise ValueError(f"Provedor desconhecido: {provedor}")
