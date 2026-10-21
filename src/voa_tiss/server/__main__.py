"""Inicie o servidor HTTP e MCP."""

from __future__ import annotations

import argparse

import uvicorn

from . import app


def main() -> None:
    """Inicie o servidor ASGI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, access_log=False)


if __name__ == "__main__":
    main()
