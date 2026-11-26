"""Every shipped engine adapter must satisfy the adapter contract (maturity PROBE).

These tests replay response shapes from upstream documentation over a MOCKED transport.
They prove the adapter logic, NOT that a real engine answers this way; see
contracts/adapters/*.md and roadmap milestone M3 (live-engine integration tests).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from nexora_core.engines import ConnectionSpec, EngineKind, HealthState, Maturity
from nexora_core.testing import assert_adapter_contract
from nexora_modules.adapters import ADAPTER_CLASSES, default_registry
from nexora_modules.adapters.probes import KafkaAdapter

pytestmark = pytest.mark.contract

HTTP_KINDS: dict[EngineKind, tuple[Any, Any]] = {
    # kind: (healthy JSON/text body, body that must degrade)
    EngineKind.TRINO: ({"starting": False}, {"starting": True}),
    EngineKind.ICEBERG_REST_CATALOG: ({"defaults": {}, "overrides": {}}, {"nope": 1}),
    EngineKind.KAFKA_CONNECT: ({"version": "3.7.0", "commit": "abc"}, {"nope": 1}),
    EngineKind.FLINK: ({"taskmanagers": 2}, {"taskmanagers": 0}),
    EngineKind.SPARK: ({"status": "ALIVE"}, {"status": "STANDBY"}),
    EngineKind.AIRFLOW: (
        {"metadatabase": {"status": "healthy"}, "scheduler": {"status": "healthy"}},
        {"metadatabase": {"status": "unhealthy"}},
    ),
    EngineKind.OPENLINEAGE: ({"namespaces": []}, {"nope": 1}),
    EngineKind.PROMETHEUS: ("Prometheus Server is Healthy.", None),
    EngineKind.OBJECT_STORE_S3: ("", None),
}
ADAPTER_BY_KIND = {cls.descriptor.kind: cls for cls in ADAPTER_CLASSES}


def build(kind: EngineKind, handler: httpx.MockTransport) -> Any:
    spec = ConnectionSpec(kind=kind, name="x", endpoint="http://engine:1234")
    return ADAPTER_BY_KIND[kind](spec, client=httpx.AsyncClient(transport=handler))


def reply(body: Any) -> httpx.Response:
    if isinstance(body, str):
        return httpx.Response(200, text=body)
    return httpx.Response(200, json=body)


async def _accept_and_close(_reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    writer.close()  # avoid leaking the server-side socket (ResourceWarning is an error here)


def test_every_engine_kind_has_exactly_one_adapter() -> None:
    assert set(ADAPTER_BY_KIND) == set(EngineKind)
    assert len(ADAPTER_CLASSES) == len(EngineKind)
    assert len(default_registry().descriptors()) == len(EngineKind)


def test_no_adapter_claims_more_than_probe_maturity() -> None:
    # Promotion to FUNCTIONAL requires verification against a real engine in CI (ADR-0004).
    assert {c.descriptor.maturity for c in ADAPTER_CLASSES} == {Maturity.PROBE}


@pytest.mark.parametrize("kind", list(HTTP_KINDS), ids=lambda k: k.value)
async def test_http_adapter_healthy_degraded_and_unreachable(kind: EngineKind) -> None:
    healthy_body, degraded_body = HTTP_KINDS[kind]

    ok_transport = httpx.MockTransport(lambda _r: reply(healthy_body))
    ok = await assert_adapter_contract(build(kind, ok_transport))
    assert ok.state is HealthState.HEALTHY

    if degraded_body is not None:
        bad_transport = httpx.MockTransport(lambda _r: reply(degraded_body))
        assert (await build(kind, bad_transport).health()).state is HealthState.DEGRADED
        html_transport = httpx.MockTransport(lambda _r: httpx.Response(200, text="<html>"))
        assert (await build(kind, html_transport).health()).state is HealthState.DEGRADED

    def refuse(_r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    down = await assert_adapter_contract(build(kind, httpx.MockTransport(refuse)))
    assert down.state is HealthState.UNHEALTHY

    server_error = httpx.MockTransport(lambda _r: httpx.Response(500))
    assert (await build(kind, server_error).health()).state is HealthState.UNHEALTHY


async def test_kafka_adapter_is_tcp_reachability_only() -> None:
    server = await asyncio.start_server(_accept_and_close, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        spec = ConnectionSpec(kind=EngineKind.KAFKA, name="k", endpoint=f"127.0.0.1:{port}")
        report = await assert_adapter_contract(KafkaAdapter(spec))
    finally:
        server.close()
        await server.wait_closed()
    assert report.state is HealthState.HEALTHY
    assert "reachability only" in report.detail
    assert KafkaAdapter.descriptor.capabilities == ("health:tcp",)
