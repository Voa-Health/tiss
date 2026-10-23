"""Cálculos determinísticos das estatísticas da referência D-TISS."""

from __future__ import annotations

from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def distribuicao(cells: dict[tuple[str, ...], list[Any]], key: tuple[str, ...]) -> list[Any]:
    return cells.setdefault(key, [0, 0, Counter(), Counter()])


def quantile(values: Counter[int], q: Decimal) -> Decimal:
    total = sum(values.values())
    position = Decimal(total - 1) * q
    lower, fraction = int(position), position % 1
    upper = lower + 1
    current = 0
    low_value = high_value = 0
    for value, count in sorted(values.items()):
        if current <= lower < current + count:
            low_value = value
        if current <= upper < current + count:
            high_value = value
            break
        current += count
    return Decimal(low_value) + (Decimal(high_value - low_value) * fraction)


def percent(numerator: int, denominator: int) -> float:
    return float(
        (Decimal(numerator) * 100 / denominator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def value_reais(value: Decimal) -> float:
    return float((value / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def estatisticas(distribution: Counter[int]) -> dict[str, Any]:
    q1 = quantile(distribution, Decimal("0.25"))
    q3 = quantile(distribution, Decimal("0.75"))
    fence = q3 + Decimal(3) * (q3 - q1)
    filtered = Counter({value: count for value, count in distribution.items() if value <= fence})
    n = sum(distribution.values())
    excluded = n - sum(filtered.values())
    return {
        "n": n,
        "mediana": value_reais(quantile(filtered, Decimal("0.5"))),
        "p25": value_reais(quantile(filtered, Decimal("0.25"))),
        "p75": value_reais(quantile(filtered, Decimal("0.75"))),
        "excluidos_pct": percent(excluded, n),
    }


def publicar(
    cells: dict[tuple[str, ...], list[Any]], semestre: str
) -> tuple[list[dict[str, Any]], int, int]:
    results = []
    suppressed = paid_published = 0
    for key, (n, pacotes, informed, paid) in sorted(cells.items()):
        if n < 30:
            suppressed += 1
            continue
        info = estatisticas(informed)
        pago = estatisticas(paid) if sum(paid.values()) >= 30 else None
        if pago:
            paid_published += 1
        results.append(
            {
                "codigo": key[0],
                "tabela": key[1],
                "uf": key[2],
                "modalidade": key[3],
                "porte": key[4],
                "semestre": semestre,
                "n": n,
                "pacote_pct": percent(pacotes, n),
                "inf_mediana": info["mediana"],
                "inf_p25": info["p25"],
                "inf_p75": info["p75"],
                "inf_excluidos_pct": info["excluidos_pct"],
                "pago_n": pago["n"] if pago else None,
                "pago_mediana": pago["mediana"] if pago else None,
                "pago_p25": pago["p25"] if pago else None,
                "pago_p75": pago["p75"] if pago else None,
                "pago_excluidos_pct": pago["excluidos_pct"] if pago else None,
            }
        )
    return results, suppressed, paid_published
