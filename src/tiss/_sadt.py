"""Renderização da guia SP/SADT em HTML e PDF."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import _line_total
from ._sadt_builders import _build_equipe, _build_solicitados
from ._sadt_bundle import load_bundle
from ._sadt_types import BundleError, MissingExtraError, SadtBundle
from ._sadt_values import (
    _clean,
    _domain_for,
    _fmt_date,
    _fmt_decimal_display,
    _fmt_money,
    _format_scalar,
    _money_scalar,
    _resolve_enum,
    _to_decimal,
)
from ._text import is_present

__all__ = [
    "BundleError",
    "MissingExtraError",
    "SadtBundle",
    "load_bundle",
    "render_sadt",
]


def _row_total(row: dict[str, Any], idx: int, matrix_name: str) -> tuple[str, str, str, Decimal]:
    """Calcula os valores exibidos e o total exato de uma linha."""
    label = f"{matrix_name}[{idx}]"
    fator_raw = row.get("fator_reducao_acrescimo")
    try:
        total = _line_total.line_total(
            unit_price=_money_scalar(row.get("valor_unitario")),
            quantity=_money_scalar(row.get("quantidade")),
            factor=fator_raw,
            field=label,
        )
    except _line_total.LineTotalError as exc:
        raise BundleError(str(exc)) from exc
    unit = _to_decimal(row.get("valor_unitario"), field=f"{label}.valor_unitario")
    fator_display = _fmt_decimal_display(fator_raw) if is_present(fator_raw) else "1.00"
    return fator_display, _fmt_money(unit), _fmt_money(total), total


def _build_executados(
    values: dict[str, Any], catalog: dict[str, Any]
) -> tuple[list[dict[str, Any]], Decimal]:
    rows = values.get("procedimentos_executados") or []
    cols = {c["key"]: c for c in catalog["matrices"]["procedimentos_executados"]["columns"]}
    out: list[dict[str, Any]] = []
    subtotal = Decimal("0.00")
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        fator_d, unit_d, total_d, total = _row_total(row, i, "procedimentos_executados")
        subtotal += total
        via = (
            _resolve_enum(
                "via_acesso", row.get("via_acesso"), _domain_for(cols["via_acesso"], catalog) or {}
            )
            if is_present(row.get("via_acesso"))
            else ""
        )
        tec = (
            _resolve_enum(
                "tecnica", row.get("tecnica"), _domain_for(cols["tecnica"], catalog) or {}
            )
            if is_present(row.get("tecnica"))
            else ""
        )
        out.append(
            {
                "sequencial": str(row.get("sequencial") or i),
                "data_execucao": _fmt_date(row.get("data_execucao")),
                "tabela": _clean(row.get("tabela")),
                "codigo": _clean(row.get("codigo")),
                "descricao": _clean(row.get("descricao")),
                "quantidade": _fmt_decimal_display(row.get("quantidade")),
                "via_acesso": via,
                "tecnica": tec,
                "fator_reducao_acrescimo": fator_d,
                "valor_unitario": unit_d,
                "valor_total": total_d,
                "equipe": _build_equipe(row, catalog),
            }
        )
    return out, subtotal


# Limite do campo de quantidade definido pelo padrão TISS.
_QUANTIDADE_MAXIMA = 999


def _despesas_meta(catalog: dict[str, Any]) -> dict[str, Any]:
    return (catalog.get("_meta", {}) or {}).get("despesas", {}) or {}


def _julgar_tabela(row: dict[str, Any], label: str, catalog: dict[str, Any]) -> str:
    """Valida a tabela informada para a linha de despesa."""
    tabela = _clean(row.get("tabela"))
    dominio = catalog.get("domains", {}).get("tabela_87_despesas", {})
    if not tabela:
        raise BundleError(
            f"{label}.tabela: linha de despesa sem tabela. Um código sem a tabela "
            "ao lado não é interpretável fora da Voa, e a guia sai da Voa."
        )
    if tabela not in dominio:
        raise BundleError(
            f"{label}.tabela: {tabela!r} não é tabela de despesa. A matriz de "
            f"Outras Despesas é das tabelas {', '.join(sorted(dominio))} da ANS "
            "(procedimento é a matriz de cima, não esta)."
        )
    return tabela


def _julgar_quantidade(row: dict[str, Any], label: str) -> str:
    """Valida a quantidade inteira aceita pela guia."""
    bruta = _money_scalar(row.get("quantidade"))
    if not is_present(bruta):
        raise BundleError(
            f"{label}.quantidade: valor obrigatório e ausente — linha precificada "
            "sem quantidade não é aviso, é linha que a guia não consegue enviar."
        )
    valor = _to_decimal(bruta, field=f"{label}.quantidade")
    if valor != valor.to_integral_value():
        raise BundleError(
            f"{label}.quantidade: {bruta!r} não é quantidade inteira. A guia não "
            "transporta fracionário — a quantidade é inteira, de no máximo três "
            "dígitos."
        )
    inteira = int(valor)
    if inteira <= 0:
        raise BundleError(
            f"{label}.quantidade: {bruta!r} não é quantidade — o que não é "
            "consumido não vira linha."
        )
    if inteira > _QUANTIDADE_MAXIMA:
        raise BundleError(
            f"{label}.quantidade: {inteira} passa do que a guia transporta. A "
            f"quantidade é inteira de no máximo três dígitos (até "
            f"{_QUANTIDADE_MAXIMA}); acima disso a operadora rejeita o lote inteiro."
        )
    return str(inteira)


def _julgar_unidade(row: dict[str, Any], label: str, tabela: str, catalog: dict[str, Any]) -> str:
    """Valida a unidade de embalagem conforme a tabela."""
    unidade = _clean(row.get("unidade_medida"))
    sistema = _clean(row.get("unidade_sistema"))
    exige = tabela in (_despesas_meta(catalog).get("exige_unidade_de_embalagem") or [])
    if exige and not unidade:
        raise BundleError(
            f"{label}.unidade_medida: a despesa {_clean(row.get('codigo'))!r} é "
            "cobrada por embalagem e chegou sem unidade (ampola, caixa, "
            "comprimido). Linha de despesa sem unidade onde a tabela a exige é "
            "glosa 5085."
        )
    if unidade and not exige:
        raise BundleError(
            f"{label}.unidade_medida: a tabela {tabela} não é cobrada por unidade "
            f"de embalagem, e a unidade {unidade!r} não se aplica a ela. Campo "
            "inesperado na linha de despesa é glosa 5084."
        )
    if unidade and sistema:
        esperado = _clean(_despesas_meta(catalog).get("sistema_da_unidade") or "") or _clean(
            next(
                (
                    c.get("default", "")
                    for c in catalog["matrices"]["outras_despesas"]["columns"]
                    if c["key"] == "unidade_sistema"
                ),
                "",
            )
        )
        if esperado and sistema != esperado:
            raise BundleError(
                f"{label}.unidade_sistema: {sistema!r} não é o sistema da Tabela 60 "
                f"da TISS ({esperado}). A unidade da linha de despesa é da T60 — "
                "um código de unidade de outro sistema não é a mesma unidade."
            )
    return unidade


def _build_despesas(
    values: dict[str, Any], catalog: dict[str, Any]
) -> tuple[list[dict[str, str]], Decimal]:
    """Monta a matriz de despesas e calcula o subtotal."""
    rows = values.get("outras_despesas") or []
    out: list[dict[str, str]] = []
    subtotal = Decimal("0.00")
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        label = f"outras_despesas[{i}]"
        tabela = _julgar_tabela(row, label, catalog)
        quantidade = _julgar_quantidade(row, label)
        unidade = _julgar_unidade(row, label, tabela, catalog)
        fator_d, unit_d, total_d, total = _row_total(row, i, "outras_despesas")
        subtotal += total
        out.append(
            {
                "sequencial": str(row.get("sequencial") or row.get("sequence") or i),
                "data": _fmt_date(row.get("data")),
                "tabela": tabela,
                "codigo": _clean(row.get("codigo")),
                "descricao": _clean(row.get("descricao")),
                "quantidade": quantidade,
                "unidade_medida": unidade,
                "fator_reducao_acrescimo": fator_d,
                "valor_unitario": unit_d,
                "valor_total": total_d,
            }
        )
    return out, subtotal


def _execucao_side_present(values: dict[str, Any], catalog: dict[str, Any]) -> bool:
    """Indica se algum campo de execução foi informado."""
    for key, spec in catalog["fields"].items():
        if spec.get("bloco") in ("contratado_executante", "atendimento") and is_present(
            values.get(key)
        ):
            return True
    return False


def build_context(
    values: dict[str, Any],
    catalog: dict[str, Any],
    *,
    gen_date: date | None = None,
    logo_src: str | None = None,
    clinic_name: str = "",
) -> dict[str, Any]:
    """Monta o contexto formatado para o template."""
    fields_spec: dict[str, dict[str, Any]] = catalog["fields"]

    # Mantém todas as chaves do catálogo no contexto.
    f: dict[str, str] = {key: "" for key in fields_spec}
    for key, spec in fields_spec.items():
        f[key] = _format_scalar(key, values.get(key), spec, catalog)

    solicitados = _build_solicitados(values)
    executados, proc_subtotal = _build_executados(values, catalog)
    despesas, desp_subtotal = _build_despesas(values, catalog)

    show_despesas = bool(despesas)
    show_execucao = bool(executados) or show_despesas or _execucao_side_present(values, catalog)

    total_geral = proc_subtotal + desp_subtotal
    totais = {
        "valor_procedimentos": _fmt_money(proc_subtotal),
        "valor_outras_despesas": _fmt_money(desp_subtotal),
        "valor_total_geral": _fmt_money(total_geral),
    }

    return {
        "f": f,
        "solicitados": solicitados,
        "executados": executados,
        "despesas": despesas,
        "show_execucao": show_execucao,
        "show_despesas": show_despesas,
        "totais": totais,
        "signatures": catalog.get("signature_areas", []),
        "logo_src": logo_src or _clean(values.get("logo_src")) or None,
        "clinic_name": clinic_name
        or _clean(values.get("clinic_name"))
        or f.get("solicitante_nome_contratado", ""),
        "gen_date": _fmt_date(gen_date or date.today()),
        "reconstructed": bool(catalog.get("_meta", {}).get("reconstructed")),
        "competencia": catalog.get("_meta", {}).get("competencia_layout", ""),
    }


def render_html(
    values: dict[str, Any],
    bundle: SadtBundle,
    *,
    gen_date: date | None = None,
    logo_src: str | None = None,
    clinic_name: str = "",
) -> str:
    """Renderiza a guia SP/SADT como HTML."""
    try:
        from jinja2 import Environment
        from markupsafe import Markup
    except ImportError as exc:
        raise MissingExtraError(
            "Instale as dependências de renderização com: pip install 'tiss[pdf]'"
        ) from exc

    ctx = build_context(
        values, bundle.catalog, gen_date=gen_date, logo_src=logo_src, clinic_name=clinic_name
    )
    # O CSS do pacote precisa permanecer sem escape HTML.
    ctx["css"] = Markup(bundle.template_css)
    env = Environment(autoescape=True)
    template = env.from_string(bundle.template_html)
    return str(template.render(**ctx))


def render_sadt(
    values: dict[str, Any],
    out_path: str | Path,
    *,
    gen_date: date | None = None,
    logo_src: str | None = None,
    clinic_name: str = "",
) -> str:
    """Gera um PDF da guia SP/SADT preenchida."""
    try:
        from weasyprint import CSS, HTML
    except ImportError as exc:
        raise MissingExtraError(
            "Instale as dependências de renderização com: pip install 'tiss[pdf]'"
        ) from exc

    bundle = load_bundle()
    html_str = render_html(
        values, bundle, gen_date=gen_date, logo_src=logo_src, clinic_name=clinic_name
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_str).write_pdf(str(out), stylesheets=[CSS(string="")])
    return str(out)
