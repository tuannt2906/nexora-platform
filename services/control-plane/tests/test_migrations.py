from __future__ import annotations

from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from nexora_control_plane.db import Base, create_db_engine
from nexora_control_plane.migrate import main, upgrade


def test_upgrade_creates_schema_and_is_idempotent(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{(tmp_path / 'm.db').as_posix()}"
    upgrade(url)
    upgrade(url)  # second run at head is a no-op
    engine = create_db_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {"engine_connections", "audit_events", "alembic_version"} <= tables
    finally:
        engine.dispose()


def test_migrations_match_orm_models(tmp_path: Path) -> None:
    """Fails when someone changes db.py without writing a migration."""
    url = f"sqlite+pysqlite:///{(tmp_path / 'd.db').as_posix()}"
    upgrade(url)
    engine = create_db_engine(url)
    try:
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()
    assert diff == []


def test_cli_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEXORA_DATABASE_URL", raising=False)
    assert main([]) == 2


def test_cli_applies_migrations(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(
        "NEXORA_DATABASE_URL", f"sqlite+pysqlite:///{(tmp_path / 'c.db').as_posix()}"
    )
    assert main([]) == 0
