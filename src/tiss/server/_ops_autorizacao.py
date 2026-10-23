from __future__ import annotations

from typing import Any, cast

import tiss
from tiss import sandbox

from ._ops_schemas import Op, _object, _string

_MESSAGE = _object({}, additional=True)
_CONTEXT = _object({}, additional=True)


def _build(value: dict[str, Any]) -> dict[str, Any]:
    xml = tiss.build_autorizacao(value["mensagem"])
    return {"xml": xml.decode("ISO-8859-1"), "hash": tiss.hash_epilogo(xml)}


def _parse(value: dict[str, Any]) -> dict[str, Any]:
    return {"mensagem": tiss.parse_autorizacao(value["xml"])}


def _check(value: dict[str, Any]) -> dict[str, Any]:
    if ("solicitacao" in value) == ("xml" in value):
        raise ValueError("Informe exatamente um dos campos 'solicitacao' ou 'xml'.")
    input_value = cast(dict[str, Any] | str, value.get("solicitacao", value.get("xml")))
    return tiss.check_autorizacao(
        input_value,
        contexto=value.get("contexto"),
    ).to_dict()


def _sandbox(value: dict[str, Any]) -> dict[str, Any]:
    if ("solicitacao" in value) == ("xml" in value):
        raise ValueError("Informe exatamente um dos campos 'solicitacao' ou 'xml'.")
    input_value = cast(dict[str, Any] | str, value.get("solicitacao", value.get("xml")))
    xml = sandbox.responder_autorizacao(input_value, cenario=value.get("cenario", "aprovado"))
    return {"xml": xml.decode("ISO-8859-1")}


AUTORIZACAO_OPS = (
    Op(
        "autorizacao_build",
        _build,
        _object({"mensagem": _MESSAGE}, ["mensagem"]),
        _object({"xml": _string(), "hash": _string()}, ["xml", "hash"]),
        "Gera XML TISS 4.03.00 para solicitação ou resposta de autorização SP/SADT.",
        1500,
        path="/v1/autorizacoes/build",
        scope="tiss:authorization",
    ),
    Op(
        "autorizacao_parse",
        _parse,
        _object({"xml": _string()}, ["xml"]),
        _object({"mensagem": _MESSAGE}, ["mensagem"]),
        "Interpreta solicitações e respostas de autorização SP/SADT.",
        1500,
        path="/v1/autorizacoes/parse",
        scope="tiss:authorization",
    ),
    Op(
        "autorizacao_check",
        _check,
        _object(
            {
                "solicitacao": _MESSAGE,
                "xml": _string(),
                "contexto": _CONTEXT,
            }
        ),
        _object({}, additional=True),
        "Valida uma solicitação SP/SADT e retorna uma decisão explicável.",
        2000,
        path="/v1/autorizacoes/check",
        scope="tiss:authorization",
    ),
    Op(
        "sandbox_autorizacao",
        _sandbox,
        _object(
            {
                "solicitacao": _MESSAGE,
                "xml": _string(),
                "cenario": {"enum": ["aprovado", "pendente", "negado"]},
            }
        ),
        _object({"xml": _string()}, ["xml"]),
        "Gera uma resposta SP/SADT sintética nos cenários disponíveis.",
        1500,
        path="/v1/sandbox/autorizacoes",
        scope="tiss:sandbox",
    ),
)


__all__ = ["AUTORIZACAO_OPS"]
