"""Aplica os níveis de acesso e a cota diária."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import urllib.request
from collections.abc import Callable
from typing import Any

from .._requisicao_segura import abrir
from ._context import CallContext
from ._keys import ANONYMOUS_LIMIT, ENTERPRISE_URL, KEYS_URL, TIER_LIMITS, Access
from ._ops_schemas import Op
from ._service import configured

Counter = Callable[[str, int], int]
_counter: Counter | None = None
_ANONYMOUS_OPERATIONS = ("sandbox_", "lista_de_espera")
_CLOUD_GUIA = "tiss_cloud_guia"


def _redis(key: str, ttl: int) -> int:
    request = urllib.request.Request(
        f"{os.environ['KV_REST_API_URL'].rstrip('/')}/pipeline",
        data=json.dumps([["INCR", key], ["EXPIRE", key, ttl]]).encode(),
        headers={"Authorization": f"Bearer {os.environ['KV_REST_API_TOKEN']}"},
    )
    with abrir(request, timeout=2) as response:
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
    return f"tiss:{day}:{hashlib.sha256(subject.encode()).hexdigest()[:32]}"


def _denied(status: int, code: str, message: str, link: str) -> tuple[int, dict[str, Any]]:
    return status, {"erro": {"codigo": code, "mensagem": message, "link": link}}


def admit(
    op_name: str, ctx: CallContext, scope: str | None = None
) -> tuple[int, dict[str, Any]] | None:
    """Devolva a recusa da chamada, ou `None` quando ela cabe no escopo e no nível."""
    access = ctx.access
    # O modo local e instalações sem backend não dependem de chaves.
    if ctx.local or not configured():
        return None
    if access is None and not op_name.startswith(_ANONYMOUS_OPERATIONS):
        return _denied(
            401, "chave_obrigatoria", "Esta operação exige chave da organização.", KEYS_URL
        )
    if access is not None and scope is not None and scope not in access.scopes:
        return _denied(403, "escopo_ausente", f"A chave não tem o escopo {scope}.", KEYS_URL)
    counter = _active_counter()
    if counter is None:
        return None
    if access is None:
        subject, limit, link = f"ip:{ctx.client_ip}", ANONYMOUS_LIMIT, KEYS_URL
    else:
        subject, limit, link = f"org:{access.org}", TIER_LIMITS[access.tier], ENTERPRISE_URL
    try:
        used = counter(_key(subject), seconds_until_reset())
    except (OSError, ValueError, LookupError, TypeError):
        return _denied(503, "cota_indisponivel", "Contagem diária indisponível.", link)
    if used > limit:
        return _denied(429, "limite_diario", f"Limite de {limit} chamadas por dia atingido.", link)
    return None


def payment_required(op: Op, access: Access | None) -> tuple[int, dict[str, Any]] | None:
    """Devolva o 402 do backend quando a op é paga e a org não tem meio de pagamento."""
    billing = access.billing if access is not None else None
    if (
        not op.paid
        or billing is None
        or not billing.enforced
        or billing.payment_method_active
        or (op.usage_kind == _CLOUD_GUIA and billing.cloud_free_remaining > 0)
    ):
        return None
    return 402, {
        "code": "payment_required",
        "detail": "Cadastre uma forma de pagamento para usar este módulo.",
        "billing_url": billing.billing_url,
    }


__all__ = ["admit", "payment_required", "seconds_until_reset", "set_counter"]
