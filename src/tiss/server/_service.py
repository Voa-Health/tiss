"""Chama o serviço de chaves e uso do backend Voa."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

Transport = Callable[[str, dict[str, Any]], Any]
_transport: Transport | None = None
_HTTP_UNAVAILABLE = 503


class ServiceError(RuntimeError):
    def __init__(self, status: int) -> None:
        super().__init__(status)
        self.status = status


def configured() -> bool:
    """Indique se o servidor valida chaves no backend; sem ele, o acesso é aberto."""
    return bool(os.environ.get("TISS_BACKEND_URL") and os.environ.get("TISS_SERVICE_SECRET"))


def set_transport(transport: Transport | None) -> None:
    global _transport  # noqa: PLW0603
    _transport = transport


def post(path: str, body: dict[str, Any]) -> Any:
    """Envie JSON ao backend e devolva a resposta, ou levante `ServiceError`."""
    if _transport is not None:
        return _transport(path, body)
    request = urllib.request.Request(
        f"{os.environ['TISS_BACKEND_URL'].rstrip('/')}{path}",
        data=json.dumps(body, separators=(",", ":")).encode(),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {os.environ['TISS_SERVICE_SECRET']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise ServiceError(exc.code) from None
    except (OSError, ValueError, KeyError):
        raise ServiceError(_HTTP_UNAVAILABLE) from None


__all__ = ["ServiceError", "Transport", "configured", "post", "set_transport"]
