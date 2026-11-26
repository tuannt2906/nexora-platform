"""Print the OpenAPI document (no database needed): ``python -m nexora_control_plane.openapi``."""

from __future__ import annotations

import json
import sys

from pydantic import SecretStr

from nexora_control_plane.app import create_app
from nexora_control_plane.settings import Settings


def build_openapi() -> dict[str, object]:
    settings = Settings(
        database_url=SecretStr("sqlite+pysqlite:///:memory:"),
        api_token=SecretStr("x" * 32),
        environment="test",
    )
    app = create_app(settings)
    schema = app.openapi()
    app.state.container.dispose()
    return schema


def render() -> str:
    return json.dumps(build_openapi(), indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    sys.stdout.write(render())
