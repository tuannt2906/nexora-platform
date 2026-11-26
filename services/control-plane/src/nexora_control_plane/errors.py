"""Maps domain errors to a single JSON error envelope: ``{"error": {code, message, details}}``."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from nexora_core.errors import (
    AdapterError,
    ConflictError,
    ForbiddenError,
    NexoraError,
    NotFoundError,
    UnauthorizedError,
    ValidationFailedError,
)
from nexora_core.logging import get_logger

_STATUS: dict[type[NexoraError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    ValidationFailedError: 422,
    UnauthorizedError: 401,
    ForbiddenError: 403,
    AdapterError: 502,
}
_log = get_logger(__name__)


def _envelope(
    status: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or {}}},
        headers=headers,
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NexoraError)
    async def _nexora(_: Request, exc: NexoraError) -> JSONResponse:
        status = next((s for t, s in _STATUS.items() if isinstance(exc, t)), 500)
        return _envelope(status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": [str(p) for p in e["loc"]], "msg": e["msg"], "type": e["type"]}
            for e in exc.errors()
        ]
        return _envelope(422, "validation_failed", "request validation failed", {"errors": errors})

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        _log.error("unhandled_error", error=type(exc).__name__, exc_info=exc)
        return _envelope(500, "internal_error", "internal server error")
