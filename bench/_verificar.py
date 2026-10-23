"""Verificadores determinísticos das tarefas do TISS-Bench."""

from __future__ import annotations

import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

import tiss
from tiss import dominio

Veredito = tuple[bool, str]

_CERCA = re.compile(r"^```[a-zA-Z]*\s*\n?(.*?)\n?```$", re.DOTALL)


def limpar(resposta: str) -> str:
    """Remove espaços e cerca de código Markdown em volta da resposta."""
    texto = resposta.strip()
    achado = _CERCA.match(texto)
    return achado.group(1).strip() if achado else texto


def normalizar(texto: str) -> str:
    """Compara textos sem acento, caixa, espaços repetidos e ponto final."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    base = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(base.casefold().split()).rstrip(".")


def centavos(valor: Any) -> int | None:
    """Converte reais em número ou texto ("100.00", "100,00") para centavos."""
    if isinstance(valor, bool):
        return None
    texto = str(valor).strip().replace("R$", "").strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        quantia = Decimal(texto)
    except InvalidOperation:
        return None
    if quantia != quantia.quantize(Decimal("0.01")):
        return None
    return int(quantia * 100)


def _json(resposta: str) -> Any:
    try:
        return json.loads(limpar(resposta))
    except (json.JSONDecodeError, TypeError):
        return None


def _ponteiro(documento: Any, ponteiro: str) -> Any:
    atual = documento
    for parte in ponteiro.lstrip("/").split("/"):
        if isinstance(atual, list) and parte.isdigit() and int(parte) < len(atual):
            atual = atual[int(parte)]
        elif isinstance(atual, dict) and parte in atual:
            atual = atual[parte]
        else:
            return None
    return atual


def _lote(esperado: dict[str, Any], resposta: str) -> Veredito:
    xml = limpar(resposta)
    if not xml.startswith("<"):
        return False, "resposta não é XML"
    relatorio = tiss.validate(xml)
    erros = sorted({f.code for f in relatorio.findings if f.severity == "error"})
    if erros:
        return False, "validate com erros: " + ", ".join(erros)
    lote = tiss.parse_lote(xml)
    if len(lote.get("guias", [])) != esperado["guias"]:
        return False, "número de guias diferente do esperado"
    for ponteiro, valor in esperado["campos"].items():
        if _ponteiro(lote, ponteiro) != valor:
            return False, f"campo divergente: {ponteiro}"
    return True, "lote válido e campos preservados"


def _hash(esperado: dict[str, Any], resposta: str) -> Veredito:
    if limpar(resposta).lower() == esperado["hash"]:
        return True, "hash correto"
    return False, "hash divergente"


def _glosa_ok(item: Any, esperado: dict[str, Any]) -> bool:
    return (
        isinstance(item, dict)
        and str(item.get("codigo", "")).strip() == esperado["codigo"]
        and normalizar(str(item.get("descricao", ""))) == normalizar(esperado["descricao"])
    )


def _glosa(esperado: dict[str, Any], resposta: str) -> Veredito:
    dados = _json(resposta)
    if "itens" not in esperado:
        if _glosa_ok(dados, esperado):
            return True, "código e motivo corretos"
        return False, "código ou motivo divergente"
    itens = dados.get("itens") if isinstance(dados, dict) else None
    if not isinstance(itens, list) or len(itens) != len(esperado["itens"]):
        return False, "lista de itens glosados divergente"
    pendentes = list(esperado["itens"])
    for item in itens:
        alvo = next(
            (
                e
                for e in pendentes
                if isinstance(item, dict)
                and str(item.get("guia", "")).strip() == e["guia"]
                and str(item.get("sequencial", "")).strip() == e["sequencial"]
                and centavos(item.get("valor_glosa")) == e["valor_glosa_centavos"]
                and _glosa_ok(item, e)
            ),
            None,
        )
        if alvo is None:
            return False, "item glosado divergente"
        pendentes.remove(alvo)
    return True, "itens glosados corretos"


def _conciliar(esperado: dict[str, Any], resposta: str) -> Veredito:
    dados = _json(resposta)
    if not isinstance(dados, dict):
        return False, "resposta não é objeto JSON"
    if "totais" in esperado:
        for campo, valor in esperado["totais"].items():
            if centavos(dados.get(campo)) != valor:
                return False, f"total divergente: {campo}"
        return True, "totais corretos"
    guias = dados.get("guias")
    if not isinstance(guias, dict) or set(guias) != set(esperado["guias"]):
        return False, "conjunto de guias divergente"
    for numero, alvo in esperado["guias"].items():
        guia = guias[numero]
        if not isinstance(guia, dict) or guia.get("decisao") != alvo["decisao"]:
            return False, f"decisão divergente na guia {numero}"
        for campo in ("valor_liberado", "valor_glosa"):
            if centavos(guia.get(campo)) != alvo[campo + "_centavos"]:
                return False, f"{campo} divergente na guia {numero}"
    return True, "conciliação correta"


def _regra(esperado: dict[str, Any], resposta: str) -> Veredito:
    if "regras" in esperado:
        dados = _json(resposta)
        if isinstance(dados, list) and sorted(map(str, dados)) == esperado["regras"]:
            return True, "regras violadas corretas"
        return False, "regras violadas divergentes"
    if "tabela" in esperado:
        codigo = limpar(resposta)
        if codigo == esperado["codigo"] and dominio.lookup(esperado["tabela"], codigo):
            return True, "código de domínio correto"
        return False, "código de domínio divergente"
    if normalizar(limpar(resposta)) == esperado["resposta"]:
        return True, "resposta correta"
    return False, "resposta divergente"


VERIFICADORES = {
    "gerar": _lote,
    "corrigir": _lote,
    "hash": _hash,
    "glosa": _glosa,
    "conciliar": _conciliar,
    "regra": _regra,
}


def verificar(tarefa: dict[str, Any], resposta: str) -> Veredito:
    """Aplica o verificador da categoria da tarefa à resposta do agente."""
    return VERIFICADORES[tarefa["categoria"]](tarefa["esperado"], resposta)
