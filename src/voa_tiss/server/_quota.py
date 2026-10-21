"""Aplica os níveis de acesso e a cota diária."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import urllib.request
from collections.abc import Callable
from typing import Any

from ._context import CallContext
from ._keys import ANONYMOUS_LIMIT, ENTERPRISE_URL, LOGIN_URL, TIER_LIMITS

Counter = Callable[[str, int], int]
_counter: Counter | None = None


def _redis(key: str, ttl: int) -> int:
    request = urllib.request.Request(
        f"{os.environ['KV_REST_API_URL'].rstrip('/')}/pipeline",
        data=json.dumps([["INCR", key], ["EXPIRE", key, ttl]]).encode(),
        headers={"Authorization": f"Bearer {os.environ['KV_REST_API_TOKEN']}"},
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        return int(json.load(response)[0]["result"])


def _active_counter() -> Counter | None:
    if _counter is not None:
        return _counter
    configured = os.environ.get("KV_REST_API_URL") and os.environ.get("KV_REST_API_TOKEN")
    return _redis if configured else None


def set_counter(counter: Counter | None) -> None:
    global _counter  # noqa: PLW0603
    _counter = counter


def seconds_until_reset() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    tomorrow = dt.datetime.combine(now.date() + dt.timedelta(days=1), dt.time(), dt.timezone.utc)
    return int((tomorrow - now).total_seconds()) + 1


def _key(subject: str) -> str:
    day = dt.datetime.now(dt.timezone.utc).date().isoformat()
    return f"voa-tiss:{day}:{hashlib.sha256(subject.encode()).hexdigest()[:32]}"


def _denied(status: int, code: str, message: str, link: str) -> tuple[int, dict[str, Any]]:
    return status, {"erro": {"codigo": code, "mensagem": message, "link": link}}


def admit(op_name: str, ctx: CallContext) -> tuple[int, dict[str, Any]] | None:
    """Devolva a recusa da chamada, ou `None` quando ela cabe no nível."""
    access = ctx.access
    # Sem segredo de chaves, o servidor é local ou auto-hospedado e não exige chave.
    if not os.environ.get("VOA_TISS_KEY_SECRET"):
        return None
    if access is None and not op_name.startswith("sandbox_"):
        return _denied(
            401, "chave_obrigatoria", "Esta operação exige chave do login Voa.", LOGIN_URL
        )
    counter = _active_counter()
    if counter is None:
        return None
    if access is None:
        subject, limit, link = f"ip:{ctx.client_ip}", ANONYMOUS_LIMIT, LOGIN_URL
    else:
        subject, limit, link = f"org:{access.org}", TIER_LIMITS[access.tier], ENTERPRISE_URL
    try:
        used = counter(_key(subject), seconds_until_reset())
    except (OSError, ValueError, LookupError, TypeError):
        return _denied(503, "cota_indisponivel", "Contagem diária indisponível.", link)
    if used > limit:
        return _denied(429, "limite_diario", f"Limite de {limit} chamadas por dia atingido.", link)
    return None


__all__ = ["admit", "seconds_until_reset", "set_counter"]
