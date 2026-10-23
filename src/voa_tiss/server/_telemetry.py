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


def _shared_lote_registry(values: Any) -> str | None:
    if not isinstance(values, list) or not values:
        return None
    registries = []
    for value in values:
        if isinstance(value, (str, bytes)):
            registry, _ = _xml_values(value)
        elif isinstance(value, dict):
            healthplan = value.get("operadora")
            registry = healthplan.get("registro_ans") if isinstance(healthplan, dict) else None
        else:
            registry = None
        if not isinstance(registry, str) or not registry:
            return None
        registries.append(registry)
    return registries[0] if len(set(registries)) == 1 else None


def _deliver(event: str, properties: dict[str, Any]) -> bool:
    sink = _sink
    if sink is not None:
        sink(event, properties)
        return True
    key = os.environ.get("POSTHOG_KEY")
    if not key:
        return False
    host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com").rstrip("/")
    event_properties = {key: value for key, value in properties.items() if key != "distinct_id"}
    body = json.dumps(
        {
            "api_key": key,
            "event": event,
            "distinct_id": properties.get("distinct_id", "voa-tiss-api"),
            "properties": event_properties,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    request = urllib.request.Request(
        f"{host}/i/v0/e/",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=2):
        pass
    return True


def _send(event: str, properties: dict[str, Any]) -> None:
    with suppress(Exception):
        _deliver(event, properties)


def waitlist_join(properties: dict[str, Any]) -> bool:
    try:
        return _deliver("tiss_waitlist_join", properties)
    except Exception:
        return False


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
    lote = entrada.get("lote")
    operadora = lote.get("operadora") if isinstance(lote, dict) else None
    lote_registry = operadora.get("registro_ans") if isinstance(operadora, dict) else None
    codes = {
        str(item["code"])
        for item in result.get("findings", [])
        if isinstance(item, dict) and item.get("code")
    }
    codes.update(
        str(item["codigo"])
        for item in result.get("linhas", [])
        if isinstance(item, dict) and item.get("codigo")
    )
    properties = {
        "operacao": operation,
        "codigos": sorted(codes),
        "registro_ans": (
            _shared_lote_registry(entrada.get("lotes"))
            if "lotes" in entrada
            else registry or entrada.get("registro_ans") or lote_registry
        ),
        "versao_tiss": result.get("version") or version,
        "data": datetime.now(timezone.utc).date().isoformat(),
        "$process_person_profile": False,
        "$geoip_disable": True,
    }
    _submit("tiss_operacao", properties, background_tasks)


__all__ = ["operation_event", "set_sink", "waitlist_join"]
