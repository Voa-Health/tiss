"""Carregamento e validação de recursos locais SP/SADT."""

from __future__ import annotations

import json
import re
from importlib.resources import files
from pathlib import Path
from typing import Any

from ._sadt_types import BundleError, SadtBundle

_MATRIX_KEYS = ("procedimentos_solicitados", "procedimentos_executados", "outras_despesas")

_FIELDS_NAME = "fields.json"

_TEMPLATE_CSS_NAME = "template.css"

_TEMPLATE_HTML_NAME = "template.html"

SADT_BUNDLE: Any = files(__package__) / "_data" / "sadt"
_F_TOKEN_RE = re.compile(r"\{\{\s*f\.([a-z0-9_]+)")


def load_catalog(catalog_path: Any) -> dict[str, Any]:
    """Carrega e verifica o catálogo de campos."""
    path = Path(catalog_path)
    if not path.is_file():
        raise BundleError(f"catálogo SP/SADT ausente em {path}.")
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BundleError(f"{path} não é JSON válido: {exc}") from exc
    if not isinstance(catalog, dict):
        raise BundleError(f"{path}: catálogo não é um objeto JSON.")
    for section in ("fields", "domains", "matrices", "totais", "signature_areas"):
        if section not in catalog:
            raise BundleError(f"{path}: seção '{section}' ausente — catálogo corrompido.")
    return catalog


def check_template_catalog_consistency(template_html: str, catalog: dict[str, Any]) -> None:
    """Compara os campos do template com o catálogo."""
    field_keys = set(catalog.get("fields", {}))
    referenced = set(_F_TOKEN_RE.findall(template_html))
    drifted = sorted(referenced - field_keys)
    if drifted:
        raise BundleError(
            f"template referencia campos ausentes do catálogo: {drifted}. "
            "template.html e fields.json divergiram — gere novamente o pacote."
        )


def load_bundle(bundle_dir: Any = SADT_BUNDLE) -> SadtBundle:
    """Carrega e verifica os recursos da guia SP/SADT."""
    root = Path(bundle_dir)
    html_path = root / _TEMPLATE_HTML_NAME
    css_path = root / _TEMPLATE_CSS_NAME
    fields_path = root / _FIELDS_NAME
    missing = [p.name for p in (html_path, css_path, fields_path) if not p.is_file()]
    if missing:
        raise BundleError(
            f"bundle SP/SADT incompleto em {root} (faltam: {', '.join(missing)}). "
            "A instalação do pacote está incompleta. O layout não é baixado em tempo de execução."
        )
    template_html = html_path.read_text(encoding="utf-8")
    template_css = css_path.read_text(encoding="utf-8")
    catalog = load_catalog(fields_path)
    check_template_catalog_consistency(template_html, catalog)
    return SadtBundle(template_html=template_html, template_css=template_css, catalog=catalog)
