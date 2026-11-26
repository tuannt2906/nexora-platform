"""Bearer-token authentication (milestone M1). OIDC/RBAC is planned (ADR-0006)."""

from __future__ import annotations

import secrets

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from nexora_control_plane.container import Container
from nexora_core.errors import UnauthorizedError

_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def require_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
    container: Container = Depends(get_container),  # noqa: B008
) -> str:
    """Returns the actor identifier recorded in the audit log."""
    expected = container.settings.api_token.get_secret_value().encode()
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), expected
    ):
        raise UnauthorizedError("missing or invalid bearer token")
    return "api-token"
