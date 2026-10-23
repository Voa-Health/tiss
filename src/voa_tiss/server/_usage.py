"""Envia ao backend o uso das chamadas autenticadas."""

from __future__ import annotations

import datetime as dt
import logging
import threading
import time
import uuid
from collections import deque

from ._keys import Access
from ._service import ServiceError, configured, post

API_CALL = "tiss_api_call"
RETRY_SECONDS = 1.0
_BATCH = 500
_MAX_ATTEMPTS = 6
_HTTP_BAD_REQUEST = 400
_HTTP_UNAVAILABLE = 503
_logger = logging.getLogger("voa_tiss.server")
_pending: deque[tuple[dict[str, object], int]] = deque()
_lock = threading.Lock()
_worker: threading.Thread | None = None


def record(access: Access, operation: str, kind: str, occurred_at: dt.datetime) -> None:
    """Enfileire o evento da chamada; o envio acontece fora da resposta."""
    global _worker  # noqa: PLW0603
    if not configured():
        return
    event: dict[str, object] = {
        "source_event_id": uuid.uuid4().hex,
        "key_id": access.key_id,
        "kind": kind,
        "occurred_at": occurred_at.isoformat(),
        "metadata": {"operation": operation},
    }
    with _lock:
        _pending.append((event, 0))
        if _worker is None:
            _worker = threading.Thread(target=_run, name="voa-tiss-usage", daemon=True)
            _worker.start()


def _send(batch: list[tuple[dict[str, object], int]]) -> bool:
    """Envie um lote e devolva se ele deve ser reenviado."""
    try:
        post("/tiss/service/usage", {"events": [event for event, _ in batch]})
    except Exception as exc:
        status = exc.status if isinstance(exc, ServiceError) else _HTTP_UNAVAILABLE
        if status == _HTTP_BAD_REQUEST:
            _logger.warning("op=usage status=400 eventos=%d", len(batch))
            return False
        retry = [(event, attempts + 1) for event, attempts in batch if attempts + 1 < _MAX_ATTEMPTS]
        if len(retry) < len(batch):
            _logger.warning("op=usage status=%d descartados=%d", status, len(batch) - len(retry))
        with _lock:
            _pending.extendleft(reversed(retry))
        return bool(retry)
    return False


def _run() -> None:
    global _worker  # noqa: PLW0603
    while True:
        with _lock:
            batch = [_pending.popleft() for _ in range(min(_BATCH, len(_pending)))]
            if not batch:
                _worker = None
                return
        if _send(batch):
            time.sleep(RETRY_SECONDS)


def wait(timeout: float) -> None:
    """Aguarde o envio pendente por até `timeout` segundos."""
    with _lock:
        worker = _worker
    if worker is not None:
        worker.join(timeout)


__all__ = ["API_CALL", "RETRY_SECONDS", "record", "wait"]
