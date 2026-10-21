from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from lxml import etree

from voa_tiss._schema import parser

_sink: Callable[[str, dict[str, Any]], None] | None = None


def set_sink(sink: Callable[[str, dict[str, Any]], None] | None) -> None:
    global _sink  # noqa: PLW0603
    _sink = sink


def _xml_values(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, (str, bytes)):
        return None, None
    try:
        raw = value.encode("utf-8") if isinstance(value, str) else value
        root = etree.fromstring(raw, parser())
    except (etree.XMLSyntaxError, TypeError, ValueError):
        return None, None
    registry = next(
        (
            node.text.strip()
            for node in root.iter()
            if isinstance(node.tag, str)
            and etree.QName(node).localname == "registroANS"
            and node.text
        ),
        None,
    )
    version = next(
        (
            node.text.strip()
            for node in root.iter()
            if isinstance(node.tag, str) and etree.QName(node).localname == "Padrao" and node.text
        ),
        None,
    )
    return registry, version


def _send(event: str, properties: dict[str, Any]) -> None:
    sink = _sink
    if sink is not None:
        with suppress(Exception):
            sink(event, properties)
        return
    key = os.environ.get("POSTHOG_KEY")
    if not key:
        return
    host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com").rstrip("/")
    body = json.dumps(
        {
            "api_key": key,
            "event": event,
            "distinct_id": "voa-tiss-api",
            "properties": properties,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    try:
        request = urllib.request.Request(
            f"{host}/i/v0/e/",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2):
            pass
    except Exception:
        pass


def _submit(
    event: str,
    properties: dict[str, Any],
    background_tasks: Any | None = None,
) -> None:
    if background_tasks is not None:
        background_tasks.add_task(_send, event, properties)
        return
    _send(event, properties)


def operation_event(
    operation: str,
    entrada: dict[str, Any],
    result: dict[str, Any],
    *,
    telemetry_off: bool,
    background_tasks: Any | None = None,
) -> None:
    if telemetry_off:
        return
    registry, version = _xml_values(entrada.get("xml"))
    properties = {
        "operacao": operation,
        "codigos": sorted(
            {
                str(item["code"])
                for item in result.get("findings", [])
                if isinstance(item, dict) and item.get("code")
            }
        ),
        "registro_ans": registry or entrada.get("registro_ans"),
        "versao_tiss": result.get("version") or version,
        "data": datetime.now(timezone.utc).date().isoformat(),
        "$process_person_profile": False,
        "$geoip_disable": True,
    }
    _submit("tiss_operacao", properties, background_tasks)


def key_issued(
    tier: str,
    *,
    telemetry_off: bool,
    background_tasks: Any | None = None,
) -> None:
    if telemetry_off:
        return
    _submit(
        "tiss_chave_emitida",
        {"tier": tier, "$process_person_profile": False, "$geoip_disable": True},
        background_tasks,
    )


__all__ = ["key_issued", "operation_event", "set_sink"]
