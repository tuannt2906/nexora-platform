"""Prometheus metrics. Label cardinality is bounded by using route TEMPLATES, not raw paths."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)


def install_metrics(app: FastAPI) -> None:
    registry = CollectorRegistry()  # per-app registry: no cross-test global state
    requests_total = Counter(
        "nexora_http_requests_total",
        "HTTP requests",
        ("method", "route", "status"),
        registry=registry,
    )
    latency = Histogram(
        "nexora_http_request_duration_seconds",
        "HTTP request latency",
        ("method", "route"),
        registry=registry,
    )

    def _route_template(request: Request) -> str:
        route = request.scope.get("route")  # set by the router once the request is matched
        return str(route.path) if route is not None else "unmatched"

    @app.middleware("http")
    async def _observe(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        route = _route_template(request)
        requests_total.labels(request.method, route, str(response.status_code)).inc()
        latency.labels(request.method, route).observe(time.perf_counter() - started)
        return response

    @app.get("/metrics", include_in_schema=False)
    def _metrics() -> Response:
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
