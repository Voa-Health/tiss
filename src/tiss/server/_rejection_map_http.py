"""Recebe mapas agregados de clientes autenticados."""

from __future__ import annotations

import asyncio
import json

import jsonschema
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import tiss

from . import _rejection_map
from ._context import CURRENT_CONTEXT
from ._keys import KEY_PREFIX
from ._service import ServiceError


def _error(status: int, code: str) -> JSONResponse:
    return JSONResponse({"code": code}, status_code=status)


async def _handle(request: Request) -> JSONResponse:
    ctx = CURRENT_CONTEXT.get()
    if ctx is None or ctx.access is None or not ctx.key.startswith(KEY_PREFIX):
        return _error(401, "key_required")
    if "tiss:rules" not in ctx.access.scopes:
        return _error(403, "scope_missing")
    org_secret = await asyncio.to_thread(_rejection_map.secret, ctx.key)
    if org_secret is None:
        return _error(403, "not_enabled")
    if request.method == "GET":
        return JSONResponse(
            {"enabled": True, "secret": org_secret}, headers={"Cache-Control": "no-store"}
        )
    try:
        value = await request.json()
        result = await asyncio.to_thread(_rejection_map.send, ctx.key, "cli", value)
    except (json.JSONDecodeError, UnicodeDecodeError, jsonschema.ValidationError):
        return _error(400, "invalid_payload")
    except ServiceError as exc:
        return _error(exc.status, "submission_failed")
    except Exception:
        return _error(503, "submission_failed")
    return JSONResponse(result)


def register_rejection_map(app: FastAPI) -> None:
    """Registre configuração e envio do mapa hospedado."""
    app.add_api_route(
        "/v1/rejection-map/config", _handle, methods=["GET"], name="rejection_map_config"
    )
    app.add_api_route(
        "/v1/rejection-map/submit",
        _handle,
        methods=["POST"],
        name="rejection_map_submit",
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": tiss.json_schema("rejection_map")}},
            }
        },
    )


__all__ = ["register_rejection_map"]
