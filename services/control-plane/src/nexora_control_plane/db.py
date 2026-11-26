"""Persistence: SQLAlchemy models + repository. Portable across PostgreSQL and SQLite."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Engine, String, Uuid, create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

from nexora_core.engines import ConnectionSpec, EngineKind
from nexora_core.errors import ConflictError, NotFoundError


class UtcDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC datetimes on every backend (SQLite drops tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("naive datetime rejected; use timezone-aware UTC")
        return value.astimezone(UTC) if value is not None else None

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ConnectionRow(Base):
    __tablename__ = "engine_connections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(63), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    options: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=_now)

    def to_spec(self) -> ConnectionSpec:
        return ConnectionSpec(
            kind=EngineKind(self.kind),
            name=self.name,
            endpoint=self.endpoint,
            secret_ref=self.secret_ref,
            options=dict(self.options),
        )


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=_now, index=True
    )
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(128), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


def create_db_engine(url: str) -> Engine:
    """Create an engine. In-memory SQLite (tests only) gets a shared single connection."""
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if parsed.database in (None, "", ":memory:"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)


class Repository:
    """All database access of the control plane. Each method is one transaction."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._sessions = sessionmaker(engine, expire_on_commit=False)

    def ping(self) -> None:
        with self._sessions() as session:
            session.execute(select(1))

    def _audit(
        self, session: Session, actor: str, action: str, target: str, detail: Mapping[str, Any]
    ) -> None:
        session.add(AuditEventRow(actor=actor, action=action, target=target, detail=dict(detail)))

    def create_connection(self, spec: ConnectionSpec, *, actor: str) -> ConnectionRow:
        row = ConnectionRow(
            name=spec.name,
            kind=spec.kind.value,
            endpoint=spec.endpoint,
            secret_ref=spec.secret_ref,
            options=dict(spec.options),
        )
        try:
            with self._sessions() as session, session.begin():
                session.add(row)
                session.flush()
                self._audit(
                    session,
                    actor,
                    "connection.created",
                    spec.name,
                    {"kind": spec.kind.value, "endpoint": spec.endpoint},
                )
        except IntegrityError:
            raise ConflictError(f"connection '{spec.name}' already exists") from None
        return row

    def list_connections(self) -> list[ConnectionRow]:
        with self._sessions() as session:
            return list(session.scalars(select(ConnectionRow).order_by(ConnectionRow.name)))

    def get_connection(self, name: str) -> ConnectionRow:
        with self._sessions() as session:
            row = session.scalars(select(ConnectionRow).where(ConnectionRow.name == name)).first()
        if row is None:
            raise NotFoundError(f"connection '{name}' not found")
        return row

    def delete_connection(self, name: str, *, actor: str) -> None:
        with self._sessions() as session, session.begin():
            row = session.scalars(select(ConnectionRow).where(ConnectionRow.name == name)).first()
            if row is None:
                raise NotFoundError(f"connection '{name}' not found")
            session.delete(row)
            self._audit(session, actor, "connection.deleted", name, {"kind": row.kind})

    def list_audit_events(self, limit: int = 100) -> list[AuditEventRow]:
        with self._sessions() as session:
            stmt = select(AuditEventRow).order_by(AuditEventRow.occurred_at.desc()).limit(limit)
            return list(session.scalars(stmt))
