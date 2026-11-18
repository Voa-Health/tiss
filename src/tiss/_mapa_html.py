"""Renderização HTML estática do mapa de rejeição."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any


def _text(value: Any) -> str:
    return escape(str(value if value is not None else "—"), quote=True)


def _value(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _table(headers: list[str], rows: list[str]) -> str:
    heading = "".join(f'<th scope="col">{_text(item)}</th>' for item in headers)
    body = "".join(rows) or f'<tr><td colspan="{len(headers)}">Sem dados</td></tr>'
    return f"<table><thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table>"


def render_rejection_map_html(mapa: dict[str, Any]) -> str:
    """Renderiza um mapa agregado em uma página HTML sem dependências."""
    providers = mapa.get("providers", [])
    lines = mapa.get("rows", [])
    providers = providers if isinstance(providers, list) else []
    lines = lines if isinstance(lines, list) else []
    summary = (
        f"<p>Lotes: <strong>{_text(mapa.get('lotes', 0))}</strong> · "
        f"Guias: <strong>{_text(mapa.get('guias', 0))}</strong> · "
        f"Ignorados: <strong>{_text(len(mapa.get('ignored', [])))}</strong></p>"
    )

    ranked_providers = sorted(
        providers,
        key=lambda item: (
            -int(item.get("guias_with_finding", 0)),
            -_value(item.get("affected_amount", "0.00")),
            str(item.get("provider", "")),
            str(item.get("month") or ""),
        ),
    )[:10]
    provider_rows = [
        "<tr>"
        f"<td>{_text(item.get('provider'))}</td>"
        f"<td>{_text(item.get('mes'))}</td>"
        f"<td>{_text(item.get('guias_with_finding', 0))}</td>"
        f"<td>{_text(item.get('affected_amount', '0.00'))}</td>"
        "</tr>"
        for item in ranked_providers
    ]

    rules: dict[tuple[str, str | None, str | None], int] = {}
    matrix: dict[tuple[str, str], dict[str, Any]] = {}
    for item in lines:
        code = str(item.get("code", ""))
        glosa = item.get("glosa")
        rule_id = item.get("rule_id")
        rule_key = (code, glosa, rule_id)
        rules[rule_key] = rules.get(rule_key, 0) + int(item.get("guias", 0))
        cell_key = (str(item.get("provider", "")), code)
        cell = matrix.setdefault(cell_key, {"guias": 0, "valor": Decimal("0.00")})
        cell["guias"] += int(item.get("guias", 0))
        cell["valor"] += _value(item.get("affected_amount", "0.00"))

    ranked_rules = sorted(
        rules.items(),
        key=lambda item: (-item[1], item[0][0], item[0][1] or "", item[0][2] or ""),
    )[:10]
    rule_rows = [
        "<tr>"
        f"<td>{_text(code)}</td>"
        f"<td>{_text(glosa)}</td>"
        f"<td>{_text(rule_id)}</td>"
        f"<td>{_text(count)}</td>"
        "</tr>"
        for (code, glosa, rule_id), count in ranked_rules
    ]

    providers_by_id = sorted({provider for provider, _ in matrix})
    codes = sorted({code for _, code in matrix})
    matrix_rows = []
    for provider in providers_by_id:
        cells = []
        for code in codes:
            value = matrix.get((provider, code))
            if value is None:
                cells.append("<td>—</td>")
            else:
                title = f"Valor afetado: {value['valor']:.2f}"
                cells.append(f'<td title="{_text(title)}">{_text(value["guias"])}</td>')
        matrix_rows.append(f'<tr><th scope="row">{_text(provider)}</th>{"".join(cells)}</tr>')
    matrix_head = ["Prestador", *codes]
    matrix_heading = "".join(f'<th scope="col">{_text(item)}</th>' for item in matrix_head)
    matrix_body = "".join(matrix_rows) or '<tr><td colspan="1">Sem dados</td></tr>'
    matrix_table = (
        f"<table><thead><tr>{matrix_heading}</tr></thead><tbody>{matrix_body}</tbody></table>"
    )

    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Mapa de rejeição</title><style>"
        "body{font:16px system-ui,sans-serif;margin:2rem auto;max-width:1100px;padding:0 1rem;"
        "color:#17212b;background:#f7f9fb}h1,h2{color:#123b5d}section{margin:2rem 0}"
        "table{border-collapse:collapse;width:100%;background:white;margin-top:1rem}"
        "th,td{border:1px solid #cbd5df;padding:.6rem;text-align:left}"
        "th{background:#eaf0f5}td{overflow-wrap:anywhere}strong{color:#123b5d}"
        "</style></head><body><main><h1>Mapa de rejeição</h1>"
        f'<section aria-label="Resumo">{summary}</section>'
        "<section><h2>Prestadores com mais retrabalho</h2>"
        f"{_table(['Prestador', 'Mês', 'Guias com achado', 'Valor afetado'], provider_rows)}"
        "</section><section><h2>Regras e códigos mais frequentes</h2>"
        f"{_table(['Código', 'Glosa', 'Regra', 'Guias'], rule_rows)}"
        f"</section><section><h2>Matriz prestador × código</h2>{matrix_table}</section>"
        "</main></body></html>"
    )


__all__ = ["render_rejection_map_html"]
