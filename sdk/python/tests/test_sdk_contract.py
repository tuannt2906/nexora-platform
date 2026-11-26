"""SDK <-> API contract: the real FastAPI app is driven through the SDK over ASGI (no sockets)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from nexora_control_plane.app import create_app
from nexora_control_plane.db import Base
from nexora_control_plane.settings import Settings
from nexora_core.engines import AdapterRegistry, ConnectionSpec
from nexora_modules.adapters.probes import TrinoAdapter
from nexora_sdk import NexoraApiError, NexoraClient
from nexora_sdk.client import OPERATIONS

pytestmark = pytest.mark.contract

TOKEN = "s" * 32
SNAPSHOT = Path(__file__).resolve().parents[3] / "contracts" / "openapi" / "control-plane.v1.json"


@pytest.fixture
async def transport() -> AsyncIterator[httpx.ASGITransport]:
    registry = AdapterRegistry()

    def factory(spec: ConnectionSpec) -> TrinoAdapter:
        transport = httpx.MockTransport(lambda _r: httpx.Response(200, json={"starting": False}))
        return TrinoAdapter(spec, client=httpx.AsyncClient(transport=transport))

    registry.register(TrinoAdapter.descriptor, factory)
    settings = Settings(
        database_url=SecretStr("sqlite+pysqlite:///:memory:"),
        api_token=SecretStr(TOKEN),
        environment="test",
        log_json=False,
        log_level="WARNING",
    )
    app = create_app(settings, registry=registry)
    Base.metadata.create_all(app.state.container.db_engine)
    yield httpx.ASGITransport(app=app)
    app.state.container.dispose()


@pytest.fixture
async def sdk(transport: httpx.ASGITransport) -> AsyncIterator[NexoraClient]:
    client = NexoraClient("http://testserver", TOKEN, transport=transport)
    yield client
    await client.aclose()


async def test_sdk_exercises_every_declared_operation(sdk: NexoraClient) -> None:
    info = await sdk.platform()
    assert info.environment == "test"
    assert len(await sdk.modules()) == 12
    adapters = await sdk.adapters()
    assert [(a.kind, a.maturity) for a in adapters] == [("trino", "probe")]
    created = await sdk.create_connection(kind="trino", name="t1", endpoint="http://trino:8080")
    assert created.name == "t1"
    assert [c.name for c in await sdk.list_connections()] == ["t1"]
    assert (await sdk.get_connection("t1")).kind == "trino"
    assert (await sdk.connection_health("t1")).health.state == "healthy"
    assert [h.name for h in await sdk.all_connection_health()] == ["t1"]
    assert [e.action for e in await sdk.audit_events(limit=5)] == ["connection.created"]
    await sdk.delete_connection("t1")
    assert await sdk.list_connections() == []


async def test_sdk_surfaces_error_envelope(
    sdk: NexoraClient, transport: httpx.ASGITransport
) -> None:
    with pytest.raises(NexoraApiError) as err:
        await sdk.get_connection("missing")
    assert (err.value.status, err.value.code) == (404, "not_found")

    async with NexoraClient("http://testserver", "wrong", transport=transport) as bad:
        with pytest.raises(NexoraApiError) as unauthorized:
            await bad.platform()
    assert unauthorized.value.status == 401


async def test_non_json_errors_are_wrapped() -> None:
    transport = httpx.MockTransport(lambda _r: httpx.Response(502, text="bad gateway"))
    async with NexoraClient("http://x", TOKEN, transport=transport) as client:
        with pytest.raises(NexoraApiError) as err:
            await client.platform()
    assert err.value.code == "http_error"


def test_every_sdk_operation_exists_in_openapi_snapshot() -> None:
    paths = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["paths"]
    for method, path in OPERATIONS:
        assert path in paths, f"SDK calls {path} which is not in the API contract"
        assert method.lower() in paths[path], f"{method} {path} missing from the API contract"
