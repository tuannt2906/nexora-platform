"""Async client for the NEXORA Control Plane API."""

from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType
from typing import Any, Self, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter

from nexora_sdk.models import (
    Adapter,
    AuditEvent,
    Connection,
    ConnectionHealth,
    Module,
    PlatformInfo,
)

T = TypeVar("T", bound=BaseModel)

#: (HTTP method, OpenAPI path template) pairs this SDK calls. Checked against the committed
#: OpenAPI snapshot by the contract tests, so the SDK cannot drift from the server silently.
OPERATIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/v1/platform"),
        ("GET", "/api/v1/modules"),
        ("GET", "/api/v1/adapters"),
        ("GET", "/api/v1/connections"),
        ("POST", "/api/v1/connections"),
        ("GET", "/api/v1/connections/{name}"),
        ("DELETE", "/api/v1/connections/{name}"),
        ("GET", "/api/v1/connections/{name}/health"),
        ("GET", "/api/v1/health/connections"),
        ("GET", "/api/v1/audit-events"),
    }
)


class NexoraApiError(Exception):
    """The API answered with an error envelope (or an unparseable error)."""

    def __init__(
        self, status: int, code: str, message: str, details: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.details = dict(details or {})


class NexoraClient:
    """Typed access to ``/api/v1``.

    >>> async with NexoraClient("https://nexora.example", token) as client:  # doctest: +SKIP
    ...     info = await client.platform()
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = await self._http.request(method, path, **kwargs)
        if response.is_success:
            return response
        try:
            error = response.json()["error"]
            raise NexoraApiError(
                response.status_code, error["code"], error["message"], error.get("details")
            )
        except (ValueError, KeyError, TypeError):
            raise NexoraApiError(
                response.status_code, "http_error", response.text[:200] or response.reason_phrase
            ) from None

    async def _get(self, path: str, model: type[T], **kwargs: Any) -> T:
        return model.model_validate((await self._request("GET", path, **kwargs)).json())

    async def _get_list(self, path: str, model: type[T], **kwargs: Any) -> list[T]:
        payload = (await self._request("GET", path, **kwargs)).json()
        return TypeAdapter(list[model]).validate_python(payload)  # type: ignore[valid-type]

    async def platform(self) -> PlatformInfo:
        return await self._get("/api/v1/platform", PlatformInfo)

    async def modules(self) -> list[Module]:
        return await self._get_list("/api/v1/modules", Module)

    async def adapters(self) -> list[Adapter]:
        return await self._get_list("/api/v1/adapters", Adapter)

    async def list_connections(self) -> list[Connection]:
        return await self._get_list("/api/v1/connections", Connection)

    async def create_connection(
        self,
        *,
        kind: str,
        name: str,
        endpoint: str,
        secret_ref: str | None = None,
        options: Mapping[str, str] | None = None,
    ) -> Connection:
        body = {
            "kind": kind,
            "name": name,
            "endpoint": endpoint,
            "secret_ref": secret_ref,
            "options": dict(options or {}),
        }
        response = await self._request("POST", "/api/v1/connections", json=body)
        return Connection.model_validate(response.json())

    async def get_connection(self, name: str) -> Connection:
        return await self._get(f"/api/v1/connections/{name}", Connection)

    async def delete_connection(self, name: str) -> None:
        await self._request("DELETE", f"/api/v1/connections/{name}")

    async def connection_health(self, name: str) -> ConnectionHealth:
        return await self._get(f"/api/v1/connections/{name}/health", ConnectionHealth)

    async def all_connection_health(self) -> list[ConnectionHealth]:
        return await self._get_list("/api/v1/health/connections", ConnectionHealth)

    async def audit_events(self, limit: int = 100) -> list[AuditEvent]:
        return await self._get_list("/api/v1/audit-events", AuditEvent, params={"limit": limit})
