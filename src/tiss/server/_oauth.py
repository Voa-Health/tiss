"""Resolve o acesso OAuth a dados abertos pelo backend Voa."""

from __future__ import annotations

import hashlib
import threading
import time

from ._keys import CACHE_SECONDS, TIER_LIMITS, Access
from ._mcp import OPEN_DATA_TOOLS
from ._ops import OPS
from ._service import ServiceError, get

_cache: dict[str, tuple[float, Access | None]] = {}
_lock = threading.Lock()
_CACHE_LIMIT = 10_000


def resolve(token: str) -> Access | None:
    if not token:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    now = time.monotonic()
    with _lock:
        cached = _cache.get(digest)
    if cached is not None and cached[0] > now:
        return cached[1]
    try:
        data = get("/oauth/tiss/identity", token)
    except ServiceError as exc:
        if exc.status != 401:
            raise
        access = None
    else:
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("organization"), dict)
            or data["organization"].get("id") in (None, "")
            or data.get("tier") not in TIER_LIMITS
        ):
            raise ServiceError(503)
        access = Access(
            key_id="",
            org=str(data["organization"]["id"]),
            tier=data["tier"],
            scopes=frozenset(
                op.scope for op in OPS if op.tool_name in OPEN_DATA_TOOLS and op.scope
            ),
        )
    with _lock:
        if len(_cache) >= _CACHE_LIMIT:
            _cache.clear()
        _cache[digest] = (now + CACHE_SECONDS, access)
    return access
