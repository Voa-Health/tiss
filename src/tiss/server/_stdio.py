"""Transporte MCP local em stdio."""

from __future__ import annotations

import anyio
from mcp.server.stdio import stdio_server

from ._context import CallContext
from ._mcp import _SHARED_INSTRUCTIONS, create_server

LOCAL_CONTEXT = CallContext(telemetry_off=True, local=True)
LOCAL_INSTRUCTIONS = (
    _SHARED_INSTRUCTIONS + " Servidor local: as tools rodam sem chave e sem telemetria; "
    "só as tools de rede/D-TISS acessam a rede."
)


async def _serve() -> None:
    server = create_server(instructions=LOCAL_INSTRUCTIONS, context=lambda: LOCAL_CONTEXT)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Inicie o servidor MCP local em stdio."""
    anyio.run(_serve)


__all__ = ["LOCAL_CONTEXT", "LOCAL_INSTRUCTIONS", "main"]
