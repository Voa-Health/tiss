"""Busca no backend Voa o pacote de regras publicado da organização."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from ._context import CallContext
from ._keys import CACHE_SECONDS, Access
from ._ops_schemas import Op
from ._service import ServiceError, configured, post

_HTTP_NOT_FOUND = 404
_HTTP_UNAVAILABLE = 503
_CACHE_LIMIT = 10_000
_logger = logging.getLogger("tiss.server")
_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}
_lock = threading.Lock()
_now = time.monotonic
_RULE_INPUTS = ("operadora", "regras", "registro_ans")


def _package(data: Any) -> dict[str, Any]:
    package = data.get("package") if isinstance(data, dict) else None
    if not isinstance(package, dict):
        raise ServiceError(_HTTP_UNAVAILABLE)
    return package


def published_rules(access: Access, key: str) -> dict[str, Any] | None:
    """Devolva o pacote publicado da org, com cache de 60 s que não guarda falhas."""
    if not configured() or not key:
        return None
    now = _now()
    with _lock:
        cached = _cache.get(access.org)
    if cached is not None and cached[0] > now:
        return cached[1]
    package: dict[str, Any] | None
    try:
        package = _package(post("/tiss/service/rules", {"key": key}))
    except Exception as exc:
        status = exc.status if isinstance(exc, ServiceError) else _HTTP_UNAVAILABLE
        if status != _HTTP_NOT_FOUND:
            _logger.warning("op=regras status=%d", status)
            return None
        package = None
    with _lock:
        if len(_cache) >= _CACHE_LIMIT:
            _cache.clear()
        _cache[access.org] = (now + CACHE_SECONDS, package)
    return package


def with_published_rules(op: Op, entrada: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    # Regras ou operadora enviadas na chamada prevalecem sobre o pacote publicado.
    if op.rules_input is None or ctx.access is None or any(k in entrada for k in _RULE_INPUTS):
        return entrada
    package = published_rules(ctx.access, ctx.key)
    return entrada if package is None else {**entrada, op.rules_input: package}


def clear_cache() -> None:
    with _lock:
        _cache.clear()


__all__ = ["clear_cache", "published_rules", "with_published_rules"]
