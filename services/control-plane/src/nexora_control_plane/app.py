"""Application factory."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from nexora_control_plane import __version__
from nexora_control_plane.container import Container
from nexora_control_plane.errors import install_error_handlers
from nexora_control_plane.metrics import install_metrics
from nexora_control_plane.routes import catalog, connections, health
from nexora_control_plane.settings import Settings
from nexora_core.engines import AdapterRegistry
from nexora_core.logging import configure_logging, get_logger


def create_app(settings: Settings, *, registry: AdapterRegistry | None = None) -> FastAPI:
    configure_logging(settings.log_level, json_output=settings.log_json)
    container = Container.build(settings, registry=registry)
    log = get_logger("nexora.control_plane")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        log.info("startup", version=__version__, environment=settings.environment)
        yield
        container.dispose()
        log.info("shutdown")

    app = FastAPI(
        title="NEXORA Control Plane API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.state.container = container

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    @app.middleware("http")
    async def _request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    install_error_handlers(app)
    install_metrics(app)
    app.include_router(health.router)
    app.include_router(catalog.router)
    app.include_router(connections.router)
    return app
