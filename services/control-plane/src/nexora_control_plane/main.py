"""ASGI entrypoint: ``uvicorn nexora_control_plane.main:app``.

Settings are read from the environment at import time; a missing/invalid secret aborts startup.
"""

from __future__ import annotations

from nexora_control_plane.app import create_app
from nexora_control_plane.settings import Settings

app = create_app(Settings())  # values come from the environment
