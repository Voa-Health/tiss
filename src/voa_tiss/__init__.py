"""Validação TISS e geração local de documentos."""

from copy import deepcopy
from typing import Any

from . import dominio, examples, operadoras
from ._audit import AuditContext, audit
from ._check import check
from ._completeness import missing_mandatory
from ._glosa import glosa
from ._lote import Lote, LoteError
from ._lote_codec import build_lote, hash_epilogo, parse_lote
from ._mapa import rejection_map
from ._patch import PatchError, apply_fixes
from ._report import Finding, Report, json_schema
from ._retorno import (
    Decisao,
    Decision,
    Proposta,
    Reconciliacao,
    RetornoError,
    parse_demonstrativo,
    plan_reconciliation,
)
from ._sadt import BundleError, MissingExtraError, load_bundle, render_sadt
from ._validate import validate

__version__ = "0.3.0"


def sadt_catalog() -> dict[str, Any]:
    """Retorna uma cópia independente do catálogo SP/SADT."""
    return deepcopy(load_bundle().catalog)


def sadt_missing(values: dict[str, Any]) -> list[str]:
    """Retorna os campos SP/SADT obrigatórios ainda ausentes."""
    return missing_mandatory(values, sadt_catalog())


__all__ = [
    "AuditContext",
    "BundleError",
    "Decisao",
    "Decision",
    "Finding",
    "Lote",
    "LoteError",
    "MissingExtraError",
    "PatchError",
    "Proposta",
    "Reconciliacao",
    "Report",
    "RetornoError",
    "apply_fixes",
    "audit",
    "build_lote",
    "check",
    "dominio",
    "examples",
    "glosa",
    "hash_epilogo",
    "json_schema",
    "operadoras",
    "parse_demonstrativo",
    "parse_lote",
    "plan_reconciliation",
    "rejection_map",
    "render_sadt",
    "sadt_catalog",
    "sadt_missing",
    "validate",
]
