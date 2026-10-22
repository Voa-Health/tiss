"""Integra a API HTTP e o endpoint MCP."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.background import BackgroundTasks
from fastapi.responses import JSONResponse
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

import voa_tiss

from ._context import CURRENT_CONTEXT, CallContext
from ._keys import KEYS_URL, LIMITS, authenticate
from ._mcp import create_mcp
from ._ops import OPS, call
from ._quota import seconds_until_reset
from ._waitlist import register_waitlist

_logger = logging.getLogger("voa_tiss.server")
_HTTP_SERVICE_UNAVAILABLE = 503
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_UNAUTHORIZED = 401
_INVALID_KEY = {
    "erro": {
        "codigo": "chave_invalida",
        "mensagem": "A chave de acesso é inválida ou foi revogada.",
        "link": KEYS_URL,
    }
}
_KEYS_UNAVAILABLE = {
    "erro": {"codigo": "chaves_indisponiveis", "mensagem": "Validação de chaves indisponível."}
}


class _MCPApp:
    def __init__(self, manager: Any) -> None:
        self.manager = manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.manager.handle_request(scope, receive, send)


def _lifespan(manager: Any) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def run(_: FastAPI) -> AsyncIterator[None]:
        async with manager.run():
            yield

    return run


def _quiet_external_loggers() -> None:
    prefixes = ("mcp", "uvicorn", "httpx", "httpcore", "h11")
    for name, candidate in logging.Logger.manager.loggerDict.items():
        if isinstance(candidate, logging.Logger) and name.startswith(prefixes):
            candidate.disabled = True
    for name in (
        "mcp",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "httpx",
        "httpcore",
        "h11",
    ):
        logging.getLogger(name).disabled = True


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"erro": {"codigo": code, "mensagem": message}},
        status_code=status,
    )


def _query_value(raw: str, schema: dict[str, Any]) -> Any:
    kind = schema.get("type")
    if kind == "integer":
        return int(raw)
    if kind == "number":
        return float(raw)
    if kind == "boolean":
        if raw.lower() not in {"true", "false"}:
            raise ValueError(f"Valor booleano inválido: {raw}")
        return raw.lower() == "true"
    return raw


def _background_tasks(path: str) -> BackgroundTasks | None:
    if path == "/mcp" or path.startswith("/mcp/"):
        return None
    return BackgroundTasks()


def _client_ip(request: Request) -> str:
    # A plataforma de hospedagem sobrescreve este header com o IP de origem.
    forwarded = request.headers.get("x-real-ip")
    return forwarded or (request.client.host if request.client else "")


async def _request_context(request: Request, call_next: Any) -> Any:
    status, access = await asyncio.to_thread(authenticate, request.headers.get("authorization"))
    if status == _HTTP_UNAUTHORIZED:
        _logger.info("op=auth status=401 ms=0.0")
        return JSONResponse(_INVALID_KEY, status_code=status)
    if status == _HTTP_SERVICE_UNAVAILABLE:
        _logger.info("op=auth status=503 ms=0.0")
        return JSONResponse(_KEYS_UNAVAILABLE, status_code=status, headers={"Retry-After": "1"})
    telemetry_off = request.headers.get("x-voa-telemetry", "").lower() == "off"
    context_token = CURRENT_CONTEXT.set(
        CallContext(
            telemetry_off=telemetry_off,
            background_tasks=_background_tasks(request.url.path),
            access=access,
            client_ip=_client_ip(request),
        )
    )
    try:
        return await call_next(request)
    finally:
        CURRENT_CONTEXT.reset(context_token)


async def _input(request: Request, operation: Any) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type == "application/xml":
        raw_values = dict(request.query_params)
        properties = operation.input_schema.get("properties", {})
        entrada = {
            key: _query_value(value, properties[key]) if key in properties else value
            for key, value in raw_values.items()
        }
        entrada["xml"] = (await request.body()).decode("utf-8")
        return entrada
    if request.method == "GET":
        raw_values = {**request.path_params, **dict(request.query_params)}
    else:
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return {}
        if not isinstance(body, dict):
            return {"_entrada": body}
        raw_values = body
    properties = operation.input_schema.get("properties", {})
    return {
        key: _query_value(value, properties[key])
        if isinstance(value, str) and key in properties
        else value
        for key, value in raw_values.items()
    }


def _endpoint(operation: Any) -> Any:
    async def handle(request: Request) -> JSONResponse:
        start = time.perf_counter()
        try:
            entrada = await _input(request, operation)
        except (UnicodeDecodeError, ValueError) as exc:
            _logger.info(
                "op=%s status=422 ms=%.1f", operation.name, (time.perf_counter() - start) * 1000
            )
            return _error(422, "entrada_invalida", str(exc))
        context = CURRENT_CONTEXT.get() or CallContext()
        status, result = await asyncio.to_thread(call, operation, entrada, context)
        retry = {_HTTP_SERVICE_UNAVAILABLE: 1, _HTTP_TOO_MANY_REQUESTS: seconds_until_reset()}
        headers = {"Retry-After": str(retry[status])} if status in retry else None
        return JSONResponse(
            result,
            status_code=status,
            headers=headers,
            background=context.background_tasks,
        )

    return handle


def _operation_openapi_extra(operation: Any) -> dict[str, Any]:
    request_body = None
    properties = operation.input_schema.get("properties", {})
    if operation.method != "GET":
        content = {"application/json": {"schema": operation.input_schema}}
        if "xml" in properties:
            content["application/xml"] = {"schema": {"type": "string"}}
        request_body = {
            "required": True,
            "content": content,
        }
    extra: dict[str, Any] = {
        "responses": {
            "200": {
                "description": "Resultado da operação.",
                "content": {"application/json": {"schema": operation.output_schema}},
            },
            "422": {"description": "Entrada inválida."},
        }
    }
    if operation.name in {"rede", "operadora_rede"}:
        extra["responses"]["503"] = {"description": "Rede hospitalar indisponível."}
    if request_body is not None:
        extra["requestBody"] = request_body
    path_parameters = re.findall(r"\{([^}]+)\}", operation.route)
    parameters = [
        {
            "name": name,
            "in": "path",
            "required": True,
            "schema": properties.get(name, {"type": "string"}),
        }
        for name in path_parameters
    ]
    if operation.method == "GET":
        required = operation.input_schema.get("required", [])
        parameters.extend(
            {
                "name": name,
                "in": "query",
                "required": name in required,
                "schema": schema,
            }
            for name, schema in properties.items()
            if name not in path_parameters
        )
    if parameters:
        extra["parameters"] = parameters
    return extra


def _register_ops(app: FastAPI) -> None:
    for operation in OPS:
        app.add_api_route(
            operation.route,
            _endpoint(operation),
            methods=[operation.method],
            name=operation.name,
            openapi_extra=_operation_openapi_extra(operation),
        )


async def _limits() -> dict[str, Any]:
    _logger.info("op=limits status=200 ms=0.0")
    return LIMITS


def create_app() -> FastAPI:
    """Crie a aplicação HTTP e MCP."""
    _quiet_external_loggers()
    mcp_manager, _ = create_mcp()
    app = FastAPI(
        title="voa-tiss",
        description="API HTTP e MCP para documentos TISS.",
        version=voa_tiss.__version__,
        lifespan=_lifespan(mcp_manager),
    )
    app.middleware("http")(_request_context)
    _register_ops(app)
    register_waitlist(app)
    app.add_api_route("/v1/limits", _limits, methods=["GET"], name="limits")
    app.router.routes.append(Route("/mcp", _MCPApp(mcp_manager), methods=["GET", "POST", "DELETE"]))
    return app


__all__ = ["create_app"]
