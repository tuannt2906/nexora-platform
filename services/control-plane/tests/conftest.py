from __future__ import annotations

from collections.abc import Callable, Iterator

import httpx
import pytest
from cp_support import AUTH, make_settings
from fastapi.testclient import TestClient

from nexora_control_plane.app import create_app
from nexora_control_plane.db import Base
from nexora_core.engines import AdapterRegistry, ConnectionSpec
from nexora_modules.adapters.probes import TrinoAdapter


@pytest.fixture
def trino_handler() -> dict[str, Callable[[httpx.Request], httpx.Response]]:
    """Mutable holder so a test can choose how the mocked Trino answers."""
    return {"fn": lambda _req: httpx.Response(200, json={"starting": False, "nodeVersion": {}})}


@pytest.fixture
def registry(
    trino_handler: dict[str, Callable[[httpx.Request], httpx.Response]],
) -> AdapterRegistry:
    reg = AdapterRegistry()

    def factory(spec: ConnectionSpec) -> TrinoAdapter:
        transport = httpx.MockTransport(lambda req: trino_handler["fn"](req))
        return TrinoAdapter(spec, client=httpx.AsyncClient(transport=transport))

    reg.register(TrinoAdapter.descriptor, factory)
    return reg


@pytest.fixture
def client(registry: AdapterRegistry) -> Iterator[TestClient]:
    app = create_app(make_settings(), registry=registry)
    Base.metadata.create_all(app.state.container.db_engine)
    with TestClient(app) as test_client:
        test_client.headers.update(AUTH)
        yield test_client
