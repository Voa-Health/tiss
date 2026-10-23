"""Calcula o total exato de uma linha de despesa."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from ._text import is_present

NEUTRAL_FACTOR = Decimal("1")


class LineTotalError(ValueError):
    """Erro em um valor obrigatório ou no total da linha."""


def to_amount(valor: Any, *, field: str) -> Decimal:
    """Converte um valor em ``Decimal`` e identifica o campo em caso de erro."""
    if not is_present(valor):
        raise LineTotalError(f"{field}: valor obrigatório e ausente")
    try:
        return Decimal(str(valor).strip())
    except (InvalidOperation, ValueError) as exc:
        raise LineTotalError(f"{field}: {valor!r} não é um número") from exc


def _fator(valor: Any, *, field: str) -> Decimal:
    """Converte o fator informado ou usa o fator neutro."""
    if not is_present(valor):
        return NEUTRAL_FACTOR
    fator = to_amount(valor, field=f"{field}.fator")
    if fator <= 0:
        raise LineTotalError(
            f"{field}.fator: {valor!r} zeraria (ou inverteria) a linha — "
            "fator de redução/acréscimo é sempre maior que zero"
        )
    return fator


def _quantidade(valor: Any, *, field: str) -> Decimal:
    quantidade = to_amount(valor, field=f"{field}.quantidade")
    if quantidade <= 0:
        raise LineTotalError(
            f"{field}.quantidade: {valor!r} não é quantidade — o que não é consumido não vira linha"
        )
    return quantidade


def line_total(
    *, unit_price: Any, quantity: Any, factor: Any = None, field: str = "linha"
) -> Decimal:
    """Calcula valor unitário × quantidade × fator sem arredondar."""
    fator = _fator(factor, field=field)
    quantidade = _quantidade(quantity, field=field)
    unitario = to_amount(unit_price, field=f"{field}.valor_unitario")
    if unitario < 0:
        raise LineTotalError(
            f"{field}.valor_unitario: {unit_price!r} é negativo — "
            "abatimento é linha própria, não preço com sinal trocado"
        )
    return unitario * quantidade * fator


def line_total_cents(
    *, unit_price_cents: Any, quantity: Any, factor: Any = None, field: str = "linha"
) -> Decimal:
    """Calcula o total usando o valor unitário em centavos."""
    return line_total(unit_price=unit_price_cents, quantity=quantity, factor=factor, field=field)


__all__ = [
    "NEUTRAL_FACTOR",
    "LineTotalError",
    "line_total",
    "line_total_cents",
    "to_amount",
]
