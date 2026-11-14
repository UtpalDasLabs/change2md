"""Vercel ASGI entrypoint with an explicit src-package path."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from change2md_server.app import app

__all__ = ["app"]
