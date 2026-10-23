"""Recebe inscrições para a lista de espera dos módulos."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import jsonschema
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tiss import operadoras

from ._context import CURRENT_CONTEXT, CallContext
from ._quota import admit, seconds_until_reset
from ._telemetry import waitlist_join

_logger = logging.getLogger("tiss.server")
_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["modulo", "email", "empresa", "volume_mensal"],
    "properties": {
        "modulo": {"enum": ["recurso", "extrator", "cloud", "analise_contas", "autorizacao"]},
        "email": {
            "type": "string",
            "maxLength": 254,
            "pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        },
        "empresa": {"type": "string", "minLength": 1, "maxLength": 200, "pattern": r"\S"},
        "volume_mensal": {
            "enum": ["ate_500", "500_a_2000", "2000_a_10000", "10000_a_50000", "acima_50000"]
        },
        "tipos_documento": {
            "type": "array",
            "items": {
                "enum": [
                    "guia_pdf",
                    "guia_foto",
                    "demonstrativo_pdf",
                    "demonstrativo_planilha",
                ]
            },
            "minItems": 1,
            "uniqueItems": True,
        },
    },
    "allOf": [
        {
            "if": {"properties": {"modulo": {"const": "extrator"}}, "required": ["modulo"]},
            "then": {"required": ["tipos_documento"]},
            "else": {"not": {"required": ["tipos_documento"]}},
        }
    ],
}
_VALIDATOR = jsonschema.Draft202012Validator(_SCHEMA, format_checker=jsonschema.FormatChecker())
_OPENAPI = {
    "summary": "Solicitar inscrição na lista de espera",
    "description": "Receba um aviso por e-mail quando o módulo for lançado.",
    "requestBody": {
        "required": True,
        "content": {"application/json": {"schema": _SCHEMA}},
    },
    "responses": {
        "202": {"description": "Inscrição recebida."},
        "422": {"description": "Entrada inválida."},
        "429": {"description": "Limite diário atingido."},
        "503": {"description": "Lista de espera indisponível."},
    },
}


async def _join_waitlist(request: Request) -> JSONResponse:
    started = time.perf_counter()
    context = CURRENT_CONTEXT.get() or CallContext()
    denied = admit("lista_de_espera", context)
    if denied is not None:
        status, result = denied
        retry = {429: seconds_until_reset(), 503: 1}
        headers = {"Retry-After": str(retry[status])} if status in retry else None
        response = JSONResponse(result, status_code=status, headers=headers)
        _logger.info(
            "op=lista_de_espera status=%d ms=%.1f", status, (time.perf_counter() - started) * 1000
        )
        return response
    try:
        entrada = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        entrada = None
    if not isinstance(entrada, dict):
        response = JSONResponse(
            {
                "erro": {
                    "codigo": "entrada_invalida",
                    "mensagem": "A entrada deve ser um objeto JSON.",
                }
            },
            status_code=422,
        )
    else:
        entrada = dict(entrada)
        if isinstance(entrada.get("email"), str):
            entrada["email"] = entrada["email"].strip().lower()
        if isinstance(entrada.get("empresa"), str):
            entrada["empresa"] = " ".join(entrada["empresa"].split())
        try:
            _VALIDATOR.validate(entrada)
        except jsonschema.ValidationError as exc:
            response = JSONResponse(
                {"erro": {"codigo": "entrada_invalida", "mensagem": exc.message}},
                status_code=422,
            )
        else:
            email = entrada["email"]
            empresa = entrada["empresa"]
            properties: dict[str, Any] = {
                "module": entrada["modulo"],
                "volume_mensal": entrada["volume_mensal"],
                "org_match": operadoras.por_email(email),
                "distinct_id": email,
                "$set": {"email": email, "empresa": empresa},
                "$geoip_disable": True,
            }
            if entrada["modulo"] == "extrator":
                properties["tipos_documento"] = entrada["tipos_documento"]
            received = await asyncio.to_thread(waitlist_join, properties)
            response = (
                JSONResponse({"recebido": True}, status_code=202)
                if received
                else JSONResponse(
                    {
                        "erro": {
                            "codigo": "lista_indisponivel",
                            "mensagem": "Lista de espera indisponível. Tente mais tarde.",
                        }
                    },
                    status_code=503,
                )
            )
    _logger.info(
        "op=lista_de_espera status=%d ms=%.1f",
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response


def register_waitlist(app: FastAPI) -> None:
    """Registre a rota pública da lista de espera."""
    app.add_api_route(
        "/v1/lista-de-espera",
        _join_waitlist,
        methods=["POST"],
        status_code=202,
        name="lista_de_espera",
        openapi_extra=_OPENAPI,
    )


__all__ = ["register_waitlist"]
