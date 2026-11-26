from __future__ import annotations

from cp_support import TOKEN
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError


def test_healthz_is_unauthenticated(client: TestClient) -> None:
    response = client.get("/healthz", headers={"Authorization": ""})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_ok_with_database(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["checks"] == {"database": "ok"}


def test_readyz_503_when_database_unreachable(client: TestClient) -> None:
    container = client.app.state.container  # type: ignore[attr-defined]

    def boom() -> None:
        raise OperationalError("select 1", {}, Exception("db down"))

    container.repository.ping = boom
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    # liveness must NOT depend on the database
    assert client.get("/healthz").status_code == 200


def test_api_requires_bearer_token(client: TestClient) -> None:
    for headers in ({"Authorization": ""}, {"Authorization": "Bearer wrong"}):
        response = client.get("/api/v1/platform", headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert response.headers["www-authenticate"] == "Bearer"


def test_api_accepts_valid_token(client: TestClient) -> None:
    response = client.get("/api/v1/platform", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200
    assert response.json()["environment"] == "test"


def test_request_id_is_echoed_and_generated(client: TestClient) -> None:
    echoed = client.get("/healthz", headers={"X-Request-ID": "abc-123"})
    assert echoed.headers["x-request-id"] == "abc-123"
    assert client.get("/healthz").headers["x-request-id"]


def test_unknown_route_uses_framework_404(client: TestClient) -> None:
    assert client.get("/nope").status_code == 404
