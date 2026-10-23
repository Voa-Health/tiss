"""Expose a aplicação ASGI para a plataforma de hospedagem."""

import os
import sys
from importlib import import_module
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
rede = Path(__file__).resolve().parents[1] / "src/tiss/rede/_data/rede.sqlite"
if rede.is_file():
    os.environ.setdefault("TISS_REDE", str(rede))
else:
    os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

app = import_module("tiss.server._http").create_app()

__all__ = ["app"]
