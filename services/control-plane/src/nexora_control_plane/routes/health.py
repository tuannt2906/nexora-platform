"""Liveness / readiness. Unauthenticated by design (kubelet, load balancers, smoke tests)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from nexora_control_plane.container import Container
from nexora_control_plane.security import get_container

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness: the process is up (no dependencies checked)")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness: dependencies required to serve traffic are reachable")
async def readyz(container: Container = Depends(get_container)) -> JSONResponse:  # noqa: B008
    try:
        await run_in_threadpool(container.repository.ping)
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503, content={"status": "not_ready", "checks": {"database": "unreachable"}}
        )
    return JSONResponse(content={"status": "ready", "checks": {"database": "ok"}})
