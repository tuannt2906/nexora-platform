"""Engine connection registry + live health probing."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query, Response
from fastapi.concurrency import run_in_threadpool

from nexora_control_plane.container import Container
from nexora_control_plane.db import AuditEventRow, ConnectionRow
from nexora_control_plane.schemas import (
    AuditEventOut,
    ConnectionCreate,
    ConnectionHealth,
    ConnectionOut,
)
from nexora_control_plane.security import get_container, require_token
from nexora_core.engines import HealthReport, HealthState

router = APIRouter(prefix="/api/v1", tags=["connections"])


async def _probe(container: Container, row: ConnectionRow) -> ConnectionHealth:
    spec = row.to_spec()
    try:
        adapter = container.registry.create(spec)
    except Exception as exc:
        report = HealthReport(state=HealthState.UNKNOWN, detail=f"adapter unavailable: {exc}")
        return ConnectionHealth(name=row.name, kind=spec.kind, maturity="planned", health=report)
    try:
        report = await adapter.health()
    finally:
        await adapter.aclose()
    return ConnectionHealth(
        name=row.name, kind=spec.kind, maturity=adapter.descriptor.maturity.value, health=report
    )


@router.get("/connections", response_model=list[ConnectionOut])
def list_connections(
    container: Container = Depends(get_container),  # noqa: B008
    _actor: str = Depends(require_token),
) -> list[ConnectionRow]:
    return container.repository.list_connections()


@router.post("/connections", response_model=ConnectionOut, status_code=201)
def create_connection(
    body: ConnectionCreate,
    container: Container = Depends(get_container),  # noqa: B008
    actor: str = Depends(require_token),
) -> ConnectionRow:
    container.registry.descriptor(body.kind)  # 404 if no adapter handles this engine kind
    return container.repository.create_connection(body.to_spec(), actor=actor)


@router.get("/connections/{name}", response_model=ConnectionOut)
def get_connection(
    name: str,
    container: Container = Depends(get_container),  # noqa: B008
    _actor: str = Depends(require_token),
) -> ConnectionRow:
    return container.repository.get_connection(name)


@router.delete("/connections/{name}", status_code=204)
def delete_connection(
    name: str,
    container: Container = Depends(get_container),  # noqa: B008
    actor: str = Depends(require_token),
) -> Response:
    container.repository.delete_connection(name, actor=actor)
    return Response(status_code=204)


@router.get("/connections/{name}/health", response_model=ConnectionHealth)
async def connection_health(
    name: str,
    container: Container = Depends(get_container),  # noqa: B008
    _actor: str = Depends(require_token),
) -> ConnectionHealth:
    row = await run_in_threadpool(container.repository.get_connection, name)
    return await _probe(container, row)


@router.get("/health/connections", response_model=list[ConnectionHealth])
async def all_connection_health(
    container: Container = Depends(get_container),  # noqa: B008
    _actor: str = Depends(require_token),
) -> list[ConnectionHealth]:
    rows = await run_in_threadpool(container.repository.list_connections)
    return list(await asyncio.gather(*(_probe(container, r) for r in rows)))


@router.get("/audit-events", response_model=list[AuditEventOut])
def audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    container: Container = Depends(get_container),  # noqa: B008
    _actor: str = Depends(require_token),
) -> list[AuditEventRow]:
    return container.repository.list_audit_events(limit)
