from __future__ import annotations

import asyncio
from typing import ClassVar

import httpx
import pytest

from nexora_core.engines import (
    ConnectionSpec,
    EngineDescriptor,
    EngineKind,
    HealthState,
    Maturity,
)
from nexora_core.http_probe import HttpProbeAdapter
from nexora_core.tcp_probe import TcpProbeAdapter, parse_host_port
from nexora_core.testing import assert_adapter_contract

DESCRIPTOR = EngineDescriptor(
    kind=EngineKind.PROMETHEUS,
    display_name="Probe under test",
    maturity=Maturity.PROBE,
    contract_doc="contracts/adapters/prometheus.md",
)


class StrictProbe(HttpProbeAdapter):
    descriptor = DESCRIPTOR
    probe_path: ClassVar[str] = "/ready"

    def validate_response(self, response: httpx.Response) -> str | None:
        return None if response.text == "ok" else "body is not ok"


def make(handler: httpx.MockTransport, **options: str) -> StrictProbe:
    connection = ConnectionSpec(
        kind=EngineKind.PROMETHEUS, name="p", endpoint="http://host:9090/", options=options
    )
    return StrictProbe(connection, client=httpx.AsyncClient(transport=handler))


async def test_healthy_when_valid_2xx() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, text="ok")

    report = await assert_adapter_contract(make(httpx.MockTransport(handler)))
    assert report.state is HealthState.HEALTHY
    assert report.latency_ms is not None
    assert seen == ["http://host:9090/ready"]  # trailing slash of endpoint is normalised


@pytest.mark.parametrize(
    ("status", "text", "expected"),
    [
        (200, "not ok", HealthState.DEGRADED),
        (404, "", HealthState.DEGRADED),
        (503, "", HealthState.UNHEALTHY),
    ],
)
async def test_status_and_body_mapping(status: int, text: str, expected: HealthState) -> None:
    probe = make(httpx.MockTransport(lambda _r: httpx.Response(status, text=text)))
    assert (await probe.health()).state is expected


async def test_transport_error_is_unhealthy_not_exception() -> None:
    def refuse(_r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    report = await make(httpx.MockTransport(refuse)).health()
    assert report.state is HealthState.UNHEALTHY
    assert "ConnectTimeout" in report.detail


async def test_probe_path_can_be_overridden_per_connection() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, text="ok")

    await make(httpx.MockTransport(handler), probe_path="/custom").health()
    assert seen == ["/custom"]


async def test_owned_client_is_closed_and_injected_client_is_not() -> None:
    connection = ConnectionSpec(kind=EngineKind.PROMETHEUS, name="p", endpoint="http://h")
    owned = StrictProbe(connection)
    await owned.aclose()
    assert owned._client.is_closed

    transport = httpx.MockTransport(lambda _r: httpx.Response(200))
    injected_client = httpx.AsyncClient(transport=transport)
    injected = StrictProbe(connection, client=injected_client)
    await injected.aclose()
    assert not injected_client.is_closed
    await injected_client.aclose()


async def _accept_and_close(_reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    writer.close()  # avoid leaking the server-side socket (ResourceWarning is an error here)


class LoopbackTcp(TcpProbeAdapter):
    descriptor = EngineDescriptor(
        kind=EngineKind.KAFKA,
        display_name="tcp",
        maturity=Maturity.PROBE,
        contract_doc="contracts/adapters/kafka.md",
    )
    default_port: ClassVar[int] = 9092


async def test_tcp_probe_against_real_loopback_listener() -> None:
    server = await asyncio.start_server(_accept_and_close, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        adapter = LoopbackTcp(
            ConnectionSpec(kind=EngineKind.KAFKA, name="k", endpoint=f"127.0.0.1:{port}")
        )
        report = await assert_adapter_contract(adapter)
        assert report.state is HealthState.HEALTHY
    finally:
        server.close()
        await server.wait_closed()


async def test_tcp_probe_unreachable_and_malformed_are_unhealthy() -> None:
    server = await asyncio.start_server(_accept_and_close, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()  # the port is now closed
    for endpoint in (f"127.0.0.1:{port}", "://"):
        adapter = LoopbackTcp(
            ConnectionSpec(kind=EngineKind.KAFKA, name="k", endpoint=endpoint), timeout=0.5
        )
        assert (await adapter.health()).state is HealthState.UNHEALTHY


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        ("broker", ("broker", 9092)),
        ("broker:19092", ("broker", 19092)),
        ("b1:9092,b2:9092", ("b1", 9092)),
        ("PLAINTEXT://b1:9093", ("b1", 9093)),
    ],
)
def test_parse_host_port(endpoint: str, expected: tuple[str, int]) -> None:
    assert parse_host_port(endpoint, 9092) == expected


@pytest.mark.parametrize("bad", ["@169.254.169.254/x", "health", "/a?b=1", "/a b", "//x/../#"])
async def test_invalid_probe_path_is_reported_without_any_request(bad: str) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, text="ok")

    report = await make(httpx.MockTransport(handler), probe_path=bad).health()
    assert report.state is HealthState.UNHEALTHY
    assert "probe_path" in report.detail
    assert calls == []  # the request must never be sent
