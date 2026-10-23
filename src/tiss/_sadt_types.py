"""Tipos de recursos SP/SADT e erros públicos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class BundleError(RuntimeError):
    """Erro no pacote SP/SADT ou nos valores da guia."""


class MissingExtraError(ImportError):
    """Dependências opcionais de PDF ausentes."""


@dataclass(frozen=True)
class SadtBundle:
    """Recursos carregados para renderizar a guia SP/SADT."""

    template_html: str
    template_css: str
    catalog: dict[str, Any]
