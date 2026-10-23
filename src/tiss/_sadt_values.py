"""Normalização de valores para a renderização SP/SADT."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from ._sadt_types import BundleError
from ._text import is_present, normalise_text


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _fmt_date(value: Any) -> str:
    """Formata datas como ``dd/mm/aaaa``."""
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    s = _clean(value)
    if not s:
        return ""
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return s


def _money_scalar(value: Any) -> Any:
    """Extrai o valor de uma estrutura monetária ou retorna o escalar."""
    if isinstance(value, dict):
        return value.get("value")
    return value


def _to_decimal(value: Any, *, field: str) -> Decimal:
    """Converte o valor em ``Decimal`` ou identifica o campo inválido."""
    s = _clean(_money_scalar(value))
    if not s:
        raise BundleError(f"{field}: valor numérico ausente — não invento valor.")
    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise BundleError(f"{field}: {s!r} não é um número válido.") from exc


def _fmt_money(value: Decimal) -> str:
    """Formata um valor com duas casas decimais."""
    return f"{value.quantize(Decimal('0.01'))}"


def _fmt_decimal_display(value: Any) -> str:
    """Preserva a quantidade ou o fator informado."""
    return _clean(value)


def _resolve_enum(field: str, value: Any, domain: dict[str, str]) -> str:
    """Resolve o código ou rótulo de um domínio fechado."""
    s = _clean(value)
    if not s:
        return ""
    if s in domain:
        return f"{s} - {domain[s]}"
    target = normalise_text(s)
    for code, label in domain.items():
        if normalise_text(label) == target or normalise_text(code) == target:
            return f"{code} - {label}"
    raise BundleError(
        f"{field}: {s!r} não é um valor válido do domínio "
        f"(esperado um de {sorted(domain)}). O renderer nunca adivinha um código — "
        "resolva o valor antes de renderizar."
    )


def _domain_for(spec: dict[str, Any], catalog: dict[str, Any]) -> dict[str, str] | None:
    """Retorna o domínio fechado de um campo, se houver."""
    dom = spec.get("dominio")
    if not dom:
        return None
    domain = catalog.get("domains", {}).get(dom)
    if domain is None:
        return None
    if not isinstance(domain, dict):
        raise BundleError(f"domínio '{dom}' não é um mapa código → rótulo — catálogo corrompido.")
    return domain


def _format_scalar(key: str, value: Any, spec: dict[str, Any], catalog: dict[str, Any]) -> str:
    """Formata um campo simples conforme o catálogo."""
    ftype = spec.get("type", "text")
    if not is_present(value):
        return ""
    if ftype == "date":
        return _fmt_date(value)
    if ftype == "money":
        return _fmt_money(_to_decimal(value, field=key))
    if ftype == "enum":
        domain = _domain_for(spec, catalog)
        if domain is None:
            return _clean(value)
        return _resolve_enum(key, value, domain)
    return _clean(value)
