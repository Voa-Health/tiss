"""Interface HTTP e MCP opcional."""

from ._http import create_app

app = create_app()

__all__ = ["app", "create_app"]
