"""Abre requisições HTTP com credencial seguindo redirects só na mesma origem."""

from __future__ import annotations

import urllib.error
import urllib.request
from http.client import HTTPMessage
from typing import IO, Any
from urllib.parse import urlsplit

_PORTAS_PADRAO = {"http": 80, "https": 443}


class RedirecionamentoRecusado(urllib.error.URLError):
    """Redirect para outra origem, recusado sem enviar a requisição."""


def _origem(url: str) -> tuple[str, str, int | None]:
    partes = urlsplit(url)
    esquema = partes.scheme.lower()
    try:
        porta = partes.port
    except ValueError:
        raise RedirecionamentoRecusado("redirecionamento com porta inválida recusado") from None
    if porta is None:
        porta = _PORTAS_PADRAO.get(esquema)
    return esquema, (partes.hostname or "").lower(), porta


class RedirecionamentoMesmaOrigem(urllib.request.HTTPRedirectHandler):
    """Segue o redirect só quando esquema, host e porta não mudam."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        if _origem(newurl) != _origem(req.full_url):
            fp.close()
            raise RedirecionamentoRecusado("redirecionamento para outra origem recusado")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_ABRIDOR = urllib.request.build_opener(RedirecionamentoMesmaOrigem)


def abrir(request: urllib.request.Request, timeout: float) -> Any:
    """Abre a requisição sem levar credenciais a outra origem."""
    return _ABRIDOR.open(request, timeout=timeout)


__all__ = ["RedirecionamentoMesmaOrigem", "RedirecionamentoRecusado", "abrir"]
