"""Needs a real PostgreSQL. Run in CI (service container) or locally with:

NEXORA_TEST_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db pytest -m integration
"""

from __future__ import annotations

import os

import pytest
from cp_support import AUTH, TRINO_BODY, make_settings
from fastapi.testclient import TestClient
from pydantic import SecretStr

from nexora_control_plane.app import create_app
from nexora_control_plane.db import Base, create_db_engine
from nexora_control_plane.migrate import upgrade

pytestmark = pytest.mark.integration

URL = os.environ.get("NEXORA_TEST_DATABASE_URL")


@pytest.fixture
def postgres_url() -> str:
    if not URL:
        pytest.skip("NEXORA_TEST_DATABASE_URL not set: Postgres integration tests NOT executed")
    engine = create_db_engine(URL)
    Base.metadata.drop_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    engine.dispose()
    return URL


def test_migrate_then_serve_on_postgres(postgres_url: str) -> None:
    upgrade(postgres_url)
    app = create_app(make_settings(database_url=SecretStr(postgres_url)))
    with TestClient(app, headers=AUTH) as client:
        assert client.get("/readyz").status_code == 200
        assert client.post("/api/v1/connections", json=TRINO_BODY).status_code == 201
        assert client.post("/api/v1/connections", json=TRINO_BODY).status_code == 409
        assert client.get("/api/v1/audit-events").json()[0]["action"] == "connection.created"
