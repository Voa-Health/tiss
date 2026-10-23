from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from ._keys import Access


@dataclass(frozen=True)
class CallContext:
    telemetry_off: bool = False
    background_tasks: Any | None = None
    access: Access | None = None
    client_ip: str = ""
    key: str = field(default="", repr=False)


CURRENT_CONTEXT: ContextVar[CallContext | None] = ContextVar("tiss_call_context", default=None)

__all__ = ["CURRENT_CONTEXT", "CallContext"]
