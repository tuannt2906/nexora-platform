"""Reusable HTTP health-probe adapter base.

A probe adapter proves exactly one thing: that an HTTP endpoint answers the engine's
documented liveness API in the documented way. Subclasses therefore only declare the
descriptor, the probe path and (optionally) a response validator.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import ClassVar

import httpx

from nexora_core.engines import ConnectionSpec, EngineAdapter, HealthReport, HealthState

DEFAULT_TIMEOUT_SECONDS = 3.0
PROBE_PATH_RE = re.compile(r"^/(?!/)[A-Za-z0-9._~%:/-]*$")

ResponseValidator = Callable[[httpx.Response], str | None]
"""Returns None when the response is acceptable, else a human-readable reason."""


class HttpProbeAdapter(EngineAdapter):
    """Probe ``GET <endpoint><probe_path>`` and map the answer to a :class:`HealthReport`."""

    probe_path: ClassVar[str] = "/"

    def __init__(
        self,
        connection: ConnectionSpec,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__(connection)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    def validate_response(self, response: httpx.Response) -> str | None:
        """Hook for engine-specific body checks. Default: any 2xx is fine."""
        return None

    @property
    def url(self) -> str:
        path = self.connection.options.get("probe_path", self.probe_path)
        return self.connection.endpoint.rstrip("/") + path

    def _path_problem(self) -> str | None:
        path = self.connection.options.get("probe_path", self.probe_path)
        if not PROBE_PATH_RE.match(path):
            return (
                "invalid probe_path (must be an absolute path without authority, query or spaces)"
            )
        return None

    async def health(self) -> HealthReport:
        problem = self._path_problem()
        if problem is not None:  # never let an option redirect the request to another host
            return HealthReport(state=HealthState.UNHEALTHY, detail=problem)
        started = time.perf_counter()
        try:
            response = await self._client.get(self.url)
        except httpx.HTTPError as exc:
            return HealthReport(state=HealthState.UNHEALTHY, detail=f"{type(exc).__name__}: {exc}")
        latency = (time.perf_counter() - started) * 1000
        if response.status_code >= 500:
            return HealthReport(
                state=HealthState.UNHEALTHY,
                detail=f"HTTP {response.status_code}",
                latency_ms=latency,
            )
        if not response.is_success:
            return HealthReport(
                state=HealthState.DEGRADED,
                detail=f"HTTP {response.status_code}",
                latency_ms=latency,
            )
        problem = self.validate_response(response)
        if problem is not None:
            return HealthReport(state=HealthState.DEGRADED, detail=problem, latency_ms=latency)
        return HealthReport(state=HealthState.HEALTHY, detail="ok", latency_ms=latency)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
