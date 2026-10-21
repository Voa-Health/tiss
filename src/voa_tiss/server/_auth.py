"""Troca o login Voa por chaves de acesso."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import secrets
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ._context import CURRENT_CONTEXT, CallContext
from ._keys import SITE_URL, TIER_LIMITS, KeyConfigurationError, issue_key, sign, unsign
from ._telemetry import key_issued

_logger = logging.getLogger("voa_tiss.server")
CLIENT_ID = f"{SITE_URL}/oauth/client.json"
REDIRECT_URI = f"{SITE_URL}/v1/auth/callback"
KEYS_PAGE = f"{SITE_URL}/chaves"
SCOPE = "voa:tiss"
_COOKIE = "voa_tiss_oauth"
_LOGIN_TTL_SECONDS = 600
_HTTP_OK = 200
_HTTP_SERVER_ERROR = 500
_NO_STORE = {"Cache-Control": "no-store"}
CLIENT_DOCUMENT = {
    "client_id": CLIENT_ID,
    "client_name": "voa-tiss",
    "client_uri": SITE_URL,
    "redirect_uris": [REDIRECT_URI],
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "token_endpoint_auth_method": "none",
    "scope": SCOPE,
}


class BackendError(RuntimeError):
    def __init__(self, status: int) -> None:
        super().__init__(status)
        self.status = status


def issuer() -> str:
    value = os.environ.get("VOA_AUTH_ISSUER", "").rstrip("/")
    if not value:
        raise BackendError(_HTTP_SERVER_ERROR)
    return value


def _backend(path: str, *, form: dict[str, str] | None = None, token: str = "") -> Any:
    """Chame o servidor de autorização e devolva o JSON, ou levante `BackendError`."""
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{issuer()}{path}",
        data=urlencode(form).encode() if form is not None else None,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise BackendError(exc.code) from None
    except (OSError, ValueError):
        raise BackendError(_HTTP_SERVER_ERROR) from None


def _tokens(form: dict[str, str]) -> dict[str, Any]:
    tokens = _backend("/oauth/token", form={**form, "client_id": CLIENT_ID, "resource": SITE_URL})
    if not isinstance(tokens, dict) or not tokens.get("access_token"):
        raise BackendError(_HTTP_SERVER_ERROR)
    return tokens


def _credentials(form: dict[str, str]) -> dict[str, Any]:
    """Troque um grant por tokens, leia a identidade e emita a chave."""
    tokens = _tokens(form)
    identity = _backend("/oauth/tiss/identity", token=tokens["access_token"])
    organization = identity.get("organization") if isinstance(identity, dict) else None
    if (
        not isinstance(organization, dict)
        or organization.get("id") in (None, "")
        or identity.get("tier") not in TIER_LIMITS
    ):
        raise BackendError(_HTTP_SERVER_ERROR)
    key, expires = issue_key(str(organization["id"]), identity["tier"])
    context = CURRENT_CONTEXT.get() or CallContext()
    key_issued(
        identity["tier"],
        telemetry_off=context.telemetry_off,
        background_tasks=context.background_tasks,
    )
    return {
        "chave": key,
        "refresh_token": tokens.get("refresh_token", ""),
        "nivel": identity["tier"],
        "expira_em": expires,
    }


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


async def _login(_: Request) -> Any:
    state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    try:
        authorize_url = f"{issuer()}/oauth/authorize"
        cookie = sign(
            "login", {"s": state, "v": verifier, "e": int(time.time()) + _LOGIN_TTL_SECONDS}
        )
    except (BackendError, KeyConfigurationError):
        _logger.info("op=auth_login status=503 ms=0.0")
        return _error(503, "login_indisponivel", "Login Voa indisponível.")
    query = urlencode(
        {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "resource": SITE_URL,
            "state": state,
            "code_challenge": _challenge(verifier),
            "code_challenge_method": "S256",
        }
    )
    response = RedirectResponse(f"{authorize_url}?{query}", status_code=302)
    response.set_cookie(
        _COOKIE,
        cookie,
        max_age=_LOGIN_TTL_SECONDS,
        path="/v1/auth",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    _logger.info("op=auth_login status=302 ms=0.0")
    return response


async def _callback(request: Request) -> RedirectResponse:
    params = request.query_params
    login = unsign("login", request.cookies.get(_COOKIE))
    fragment: dict[str, Any] = {"erro": "login_invalido"}
    try:
        expected = issuer()
    except BackendError:
        expected = ""
    if (
        expected
        and login is not None
        and params.get("code")
        and secrets.compare_digest(params.get("state", ""), login["s"])
        and params.get("iss", expected) == expected
    ):
        form = {
            "grant_type": "authorization_code",
            "code": params["code"],
            "code_verifier": login["v"],
            "redirect_uri": REDIRECT_URI,
        }
        try:
            fragment = await asyncio.to_thread(_credentials, form)
        except BackendError:
            fragment = {"erro": "login_recusado"}
    context = CURRENT_CONTEXT.get() or CallContext()
    response = RedirectResponse(
        f"{KEYS_PAGE}#{urlencode(fragment)}",
        status_code=302,
        headers=_NO_STORE,
        background=context.background_tasks,
    )
    response.delete_cookie(_COOKIE, path="/v1/auth")
    _logger.info("op=auth_callback status=302 ms=0.0")
    return response


async def _refresh(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError:
        body = None
    token = body.get("refresh_token") if isinstance(body, dict) else None
    if not isinstance(token, str) or not token:
        _logger.info("op=keys_refresh status=422 ms=0.0")
        return _error(422, "entrada_invalida", "Informe refresh_token.")
    try:
        result = await asyncio.to_thread(
            _credentials, {"grant_type": "refresh_token", "refresh_token": token}
        )
    except BackendError as exc:
        status = 503 if exc.status >= _HTTP_SERVER_ERROR else 401
        _logger.info("op=keys_refresh status=%d ms=0.0", status)
        if status == 401:
            return _error(401, "acesso_revogado", "Entre novamente com a conta Voa.")
        return _error(503, "login_indisponivel", "Login Voa indisponível.")
    context = CURRENT_CONTEXT.get() or CallContext()
    _logger.info("op=keys_refresh status=200 ms=0.0")
    return JSONResponse(result, headers=_NO_STORE, background=context.background_tasks)


async def _client_document() -> dict[str, Any]:
    return CLIENT_DOCUMENT


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"erro": {"codigo": code, "mensagem": message}},
        status_code=status,
        headers=_NO_STORE,
    )


def register_auth(app: FastAPI) -> None:
    app.add_api_route("/v1/auth/login", _login, methods=["GET"], name="auth_login")
    app.add_api_route("/v1/auth/callback", _callback, methods=["GET"], name="auth_callback")
    app.add_api_route("/oauth/client.json", _client_document, methods=["GET"], name="oauth_client")
    app.add_api_route(
        "/v1/keys/refresh",
        _refresh,
        methods=["POST"],
        name="refresh_key",
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["refresh_token"],
                            "properties": {"refresh_token": {"type": "string"}},
                        }
                    }
                },
            }
        },
    )


__all__ = ["CLIENT_DOCUMENT", "BackendError", "register_auth"]
