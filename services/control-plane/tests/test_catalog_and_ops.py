from __future__ import annotations

from cp_support import AUTH, make_settings
from fastapi.testclient import TestClient

from nexora_control_plane.app import create_app


def test_modules_catalog_is_served_from_module_toml(client: TestClient) -> None:
    modules = client.get("/api/v1/modules").json()
    assert len(modules) == 12
    assert {"id", "maturity", "acceptance", "public_interfaces"} <= modules[0].keys()


def test_adapters_catalog_lists_honest_maturity() -> None:
    app = create_app(make_settings())  # default registry: every adapter shipped
    with TestClient(app) as client:
        adapters = client.get("/api/v1/adapters", headers=AUTH).json()
    assert len(adapters) == 10
    assert {a["maturity"] for a in adapters} == {"probe"}  # nothing is claimed FUNCTIONAL


def test_metrics_exposed_with_bounded_labels(client: TestClient) -> None:
    client.get("/api/v1/connections/some-name")
    body = client.get("/metrics").text
    assert "nexora_http_requests_total" in body
    assert 'route="/api/v1/connections/{name}"' in body
    assert "some-name" not in body  # a raw path never becomes a label


def test_docs_disabled_in_production() -> None:
    app = create_app(make_settings(environment="production"))
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_docs_enabled_outside_production(client: TestClient) -> None:
    assert client.get("/openapi.json").status_code == 200


def test_cors_only_for_configured_origins() -> None:
    app = create_app(make_settings(cors_origins=["https://nexora.example"]))
    with TestClient(app) as client:
        ok = client.get("/healthz", headers={"Origin": "https://nexora.example"})
        bad = client.get("/healthz", headers={"Origin": "https://evil.example"})
    assert ok.headers["access-control-allow-origin"] == "https://nexora.example"
    assert "access-control-allow-origin" not in bad.headers
