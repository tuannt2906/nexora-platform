"""Alembic environment. The connection is injected by ``nexora_control_plane.migrate``."""

from __future__ import annotations

from alembic import context
from sqlalchemy import Connection

from nexora_control_plane.db import Base

target_metadata = Base.metadata


def run_migrations() -> None:
    connection: Connection | None = context.config.attributes.get("connection")
    if connection is None:
        raise RuntimeError("run migrations via `python -m nexora_control_plane.migrate`")
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


run_migrations()
