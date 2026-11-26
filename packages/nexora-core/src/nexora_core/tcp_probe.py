"""TCP reachability probe for engines without an HTTP liveness API (e.g. Kafka brokers).

This is the weakest honest signal: "something accepts TCP connections on that address".
Adapters built on it must say so in their descriptor/contract document.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import ClassVar
from urllib.parse import urlparse

from nexora_core.engines import ConnectionSpec, EngineAdapter, HealthReport, HealthState

DEFAULT_TIMEOUT_SECONDS = 3.0


def parse_host_port(endpoint: str, default_port: int) -> tuple[str, int]:
    """Accept ``host``, ``host:port`` or ``scheme://host:port`` (first host of a comma list)."""
    first = endpoint.split(",")[0].strip()
    parsed = urlparse(first if "://" in first else f"//{first}")
    host = parsed.hostname
    if not host:
        raise ValueError(f"cannot parse host from endpoint {endpoint!r}")
    return host, parsed.port or default_port


class TcpProbeAdapter(EngineAdapter):
    default_port: ClassVar[int] = 0

    def __init__(
        self, connection: ConnectionSpec, *, timeout: float = DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        super().__init__(connection)
        self._timeout = timeout

    async def health(self) -> HealthReport:
        started = time.perf_counter()
        try:
            host, port = parse_host_port(self.connection.endpoint, self.default_port)
            _reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=self._timeout
            )
        except (OSError, TimeoutError, ValueError) as exc:
            return HealthReport(state=HealthState.UNHEALTHY, detail=f"{type(exc).__name__}: {exc}")
        writer.close()
        with contextlib.suppress(OSError):  # a peer reset during close is not a health signal
            await writer.wait_closed()
        return HealthReport(
            state=HealthState.HEALTHY,
            detail="tcp connect ok (reachability only)",
            latency_ms=(time.perf_counter() - started) * 1000,
        )
