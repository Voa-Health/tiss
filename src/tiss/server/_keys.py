"""Valida as chaves de organização no backend Voa."""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass
from typing import Any

from ._service import ServiceError, configured, post

KEY_PREFIX = "sk_voa_"
KEY_PREFIXES = (KEY_PREFIX, "sk_tiss_")
CACHE_SECONDS = 60
ANONYMOUS_LIMIT = 10
TIER_LIMITS = {"login": 50, "verified": 1_000}
SITE_URL = "https://tiss-api.voa.health"
KEYS_URL = f"{SITE_URL}/org"
BILLING_URL = f"{KEYS_URL}/cobranca"
ENTERPRISE_URL = "https://voa.health"
LIMITS = {
    "limite_diario": None,
    "sem_chave": {"operacoes": ["sandbox_*", "lista_de_espera"], "chaves": KEYS_URL},
    "niveis": sorted(TIER_LIMITS),
    "chave": {
        "prefixo": KEY_PREFIX,
        "prefixos_aceitos": list(KEY_PREFIXES),
        "revogacao_segundos": CACHE_SECONDS,
    },
    "chave_invalida": {"status": 401},
    "escopo_ausente": {"status": 403},
}
_CACHE_LIMIT = 10_000
_HTTP_OK = 200
_HTTP_UNAUTHORIZED = 401
_HTTP_UNAVAILABLE = 503
_cache: dict[str, tuple[float, Access | None]] = {}
_lock = threading.Lock()
_now = time.monotonic


@dataclass(frozen=True)
class Billing:
    enforced: bool
    payment_method_active: bool
    billing_url: str
    cloud_free_remaining: int


@dataclass(frozen=True)
class Access:
    key_id: str
    org: str
    tier: str
    scopes: frozenset[str]
    billing: Billing | None = None


def _billing(value: Any) -> Billing | None:
    if not isinstance(value, dict):
        return None
    url = value.get("billing_url")
    remaining = value.get("cloud_free_remaining")
    return Billing(
        enforced=value.get("enforced") is True,
        payment_method_active=value.get("payment_method_active") is True,
        billing_url=url if isinstance(url, str) and url else BILLING_URL,
        cloud_free_remaining=(
            remaining if isinstance(remaining, int) and not isinstance(remaining, bool) else 0
        ),
    )


def _access(data: Any) -> Access | None:
    if not isinstance(data, dict) or "active" not in data:
        raise ServiceError(_HTTP_UNAVAILABLE)
    if data["active"] is not True:
        return None
    organization = data.get("organization")
    scopes = data.get("scopes")
    if (
        not isinstance(organization, dict)
        or organization.get("id") in (None, "")
        or data.get("key_id") in (None, "")
        or data.get("tier") not in TIER_LIMITS
        or not isinstance(scopes, list)
    ):
        raise ServiceError(_HTTP_UNAVAILABLE)
    return Access(
        key_id=str(data["key_id"]),
        org=str(organization["id"]),
        tier=data["tier"],
        scopes=frozenset(str(scope) for scope in scopes),
        billing=_billing(data.get("billing")),
    )


def resolve(key: str) -> Access | None:
    """Devolva o acesso da chave, consultando o backend no máximo uma vez a cada 60 s."""
    if not key.startswith(KEY_PREFIXES):
        return None
    digest = hashlib.sha256(key.encode()).hexdigest()
    now = _now()
    with _lock:
        cached = _cache.get(digest)
    if cached is not None and cached[0] > now:
        return cached[1]
    access = _access(post("/tiss/service/keys/introspect", {"key": key}))
    with _lock:
        if len(_cache) >= _CACHE_LIMIT:
            for stale in [item for item, (expires, _) in _cache.items() if expires <= now]:
                del _cache[stale]
            if len(_cache) >= _CACHE_LIMIT:
                _cache.clear()
        _cache[digest] = (now + CACHE_SECONDS, access)
    return access


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def bearer_key(header: str | None) -> str:
    prefix, _, value = (header or "").partition(" ")
    return value.strip() if prefix.lower() == "bearer" else ""


def authenticate(header: str | None) -> tuple[int, Access | None]:
    """Separe pedido sem chave, chave válida, chave inválida e backend indisponível."""
    if header is None or not configured():
        return _HTTP_OK, None
    try:
        access = resolve(bearer_key(header))
    except ServiceError:
        return _HTTP_UNAVAILABLE, None
    return (_HTTP_OK, access) if access is not None else (_HTTP_UNAUTHORIZED, None)


__all__ = [
    "ANONYMOUS_LIMIT",
    "BILLING_URL",
    "CACHE_SECONDS",
    "ENTERPRISE_URL",
    "KEYS_URL",
    "KEY_PREFIX",
    "KEY_PREFIXES",
    "LIMITS",
    "SITE_URL",
    "TIER_LIMITS",
    "Access",
    "Billing",
    "authenticate",
    "bearer_key",
    "clear_cache",
    "resolve",
]
