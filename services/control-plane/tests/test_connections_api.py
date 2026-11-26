from __future__ import annotations

from collections.abc import Callable

import httpx
from cp_support import TRINO_BODY
from fastapi.testclient import TestClient

Handler = dict[str, Callable[[httpx.Request], httpx.Response]]


def test_connection_lifecycle_and_audit(client: TestClient) -> None:
    created = client.post("/api/v1/connections", json=TRINO_BODY)
    assert created.status_code == 201
    assert created.json()["name"] == "trino-main"

    assert [c["name"] for c in client.get("/api/v1/connections").json()] == ["trino-main"]
    assert client.get("/api/v1/connections/trino-main").json()["kind"] == "trino"

    assert client.delete("/api/v1/connections/trino-main").status_code == 204
    assert client.get("/api/v1/connections/trino-main").status_code == 404
    assert client.delete("/api/v1/connections/trino-main").status_code == 404

    actions = [e["action"] for e in client.get("/api/v1/audit-events").json()]
    assert sorted(actions) == ["connection.created", "connection.deleted"]


def test_duplicate_name_conflicts(client: TestClient) -> None:
    assert client.post("/api/v1/connections", json=TRINO_BODY).status_code == 201
    response = client.post("/api/v1/connections", json=TRINO_BODY)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_engine_kind_without_adapter_is_404(client: TestClient) -> None:
    body = {**TRINO_BODY, "kind": "flink", "name": "flink-a"}  # test registry only has trino
    response = client.post("/api/v1/connections", json=body)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_validation_errors_use_envelope(client: TestClient) -> None:
    response = client.post("/api/v1/connections", json={**TRINO_BODY, "name": "Bad Name"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_ssrf_sensitive_endpoints_rejected(client: TestClient) -> None:
    for endpoint in (
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/",
        "file:///etc/passwd",
        "gopher://x:1",
        "bad endpoint with spaces",
    ):
        response = client.post("/api/v1/connections", json={**TRINO_BODY, "endpoint": endpoint})
        assert response.status_code == 422, endpoint


def test_extra_fields_forbidden(client: TestClient) -> None:
    response = client.post("/api/v1/connections", json={**TRINO_BODY, "password": "hunter2"})
    assert response.status_code == 422


def test_health_probe_healthy_degraded_unhealthy(
    client: TestClient, trino_handler: Handler
) -> None:
    client.post("/api/v1/connections", json=TRINO_BODY)

    healthy = client.get("/api/v1/connections/trino-main/health").json()
    assert healthy["health"]["state"] == "healthy"
    assert healthy["maturity"] == "probe"

    trino_handler["fn"] = lambda _r: httpx.Response(200, json={"starting": True})
    degraded = client.get("/api/v1/connections/trino-main/health").json()
    assert degraded["health"]["state"] == "degraded"

    def refuse(_r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    trino_handler["fn"] = refuse
    down = client.get("/api/v1/health/connections").json()
    assert down[0]["health"]["state"] == "unhealthy"


def test_health_of_missing_connection_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/connections/missing/health").status_code == 404


def test_probe_path_cannot_redirect_the_probe_to_another_host(client: TestClient) -> None:
    for bad in ("@169.254.169.254/latest", "health", "//evil.example/x", "/a?b=c", "/a b", "/x#f"):
        body = {**TRINO_BODY, "options": {"probe_path": bad}}
        response = client.post("/api/v1/connections", json=body)
        assert response.status_code == 422, bad
    ok = client.post(
        "/api/v1/connections", json={**TRINO_BODY, "options": {"probe_path": "/custom/health"}}
    )
    assert ok.status_code == 201


def test_credentials_in_endpoint_are_rejected(client: TestClient) -> None:
    body = {**TRINO_BODY, "endpoint": "http://admin:hunter2@trino:8080"}  # pragma: allowlist secret
    response = client.post("/api/v1/connections", json=body)
    assert response.status_code == 422
    assert "hunter2" not in response.text
