"""Coleta opt-in de agregados por organização."""

from __future__ import annotations

import hashlib
import re
import threading
import time
from typing import Any

import jsonschema

import tiss

from ._context import CallContext
from ._keys import CACHE_SECONDS, KEY_PREFIX
from ._ops_schemas import Op
from ._published_rules import with_published_rules
from ._service import configured, post

_cache: dict[str, tuple[float, str | None]] = {}
_lock = threading.Lock()
_slots = threading.BoundedSemaphore(4)
_now = time.monotonic
_VALIDATOR = jsonschema.Draft202012Validator(tiss.json_schema("rejection_map"))


def secret(key: str) -> str | None:
    """Consulte o opt-in por chave, com cache de 60 segundos."""
    if not configured() or not key.startswith(KEY_PREFIX):
        return None
    digest = hashlib.sha256(key.encode()).hexdigest()
    now = _now()
    with _lock:
        cached = _cache.get(digest)
    if cached is not None and cached[0] > now:
        return cached[1]
    value = None
    try:
        data = post("/tiss/service/rejection-map/config", {"key": key})
        if isinstance(data, dict) and data.get("enabled") is True:
            candidate = data.get("secret")
            if isinstance(candidate, str) and re.fullmatch(r"[0-9a-f]{64}", candidate):
                value = candidate
    except Exception:
        pass
    with _lock:
        if len(_cache) >= 10_000:
            _cache.clear()
        _cache[digest] = (now + CACHE_SECONDS, value)
    return value


def clear_cache() -> None:
    """Limpe as configurações em memória."""
    with _lock:
        _cache.clear()


def send(key: str, source: str, value: Any) -> Any:
    """Valide e envie somente o mapa agregado ao backend."""
    _VALIDATOR.validate(value)
    return post("/tiss/service/rejection-map", {"key": key, "source": source, "map": value})


def _collect(entrada: dict[str, Any], key: str) -> None:
    try:
        org_secret = secret(key)
        if org_secret is None:
            return
        value = tiss.rejection_map(
            [entrada["lote"] if "lote" in entrada else entrada["xml"]],
            contexto=entrada.get("contexto"),
            operadora=entrada.get("operadora"),
            segredo_pseudonimo=org_secret,
            at=entrada.get("data"),
        )
        if value["ignorados"]:
            return
        send(key, "server", value)
    except Exception:
        pass
    finally:
        _slots.release()


def collect(operation: str, entrada: dict[str, Any], ctx: CallContext) -> None:
    """Agende coleta limitada em memória, sem aguardar rede ou agregação."""
    if operation not in {"validate", "audit"} or ctx.access is None:
        return
    if not ctx.key.startswith(KEY_PREFIX) or not configured() or not _slots.acquire(False):
        return
    try:
        threading.Thread(
            target=_collect, args=(entrada, ctx.key), name="tiss-map", daemon=True
        ).start()
    except Exception:
        _slots.release()


def run_with_collection(op: Op, entrada: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    """Execute com regras publicadas e agende coleta após uma operação válida."""
    effective_input = with_published_rules(op, entrada, ctx)
    result = op.run(effective_input)
    collect(op.name, effective_input, ctx)
    return result


__all__ = ["clear_cache", "collect", "run_with_collection", "secret", "send"]
