"""Shared constants/helpers for control-plane tests (importable via pytest `pythonpath`)."""

from __future__ import annotations

from pydantic import SecretStr

from nexora_control_plane.settings import Settings
from nexora_core.engines import EngineKind

TOKEN = "t" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}
TRINO_BODY = {"kind": EngineKind.TRINO.value, "name": "trino-main", "endpoint": "http://trino:8080"}


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": SecretStr("sqlite+pysqlite:///:memory:"),
        "api_token": SecretStr(TOKEN),
        "environment": "test",
        "log_json": False,
        "log_level": "WARNING",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]
