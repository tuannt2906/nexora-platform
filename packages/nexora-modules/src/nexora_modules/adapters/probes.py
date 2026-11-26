"""Health-probe adapters for third-party engines (maturity: PROBE).

What "PROBE" means here, precisely:
* the adapter calls the engine's documented liveness/info endpoint and interprets the answer;
* behaviour is verified in unit/contract tests against a MOCKED HTTP transport that replays
  the response shape taken from upstream documentation;
* it has NOT been verified against a live engine. That verification is the job of the
  integration suite (roadmap milestone M3) and is what promotes an adapter to FUNCTIONAL.

Nothing here executes queries, submits jobs or touches data.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

import httpx

from nexora_core.engines import EngineDescriptor, EngineKind, Maturity
from nexora_core.http_probe import HttpProbeAdapter
from nexora_core.tcp_probe import TcpProbeAdapter


def _json_object(response: httpx.Response) -> dict[str, Any] | None:
    try:
        body = json.loads(response.content)
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def _descriptor(
    kind: EngineKind, name: str, capabilities: tuple[str, ...] = ("health",)
) -> EngineDescriptor:
    return EngineDescriptor(
        kind=kind,
        display_name=name,
        maturity=Maturity.PROBE,
        capabilities=capabilities,
        contract_doc=f"contracts/adapters/{kind.value}.md",
    )


class TrinoAdapter(HttpProbeAdapter):
    """Trino coordinator: ``GET /v1/info`` -> ``{"starting": false, ...}``."""

    descriptor = _descriptor(EngineKind.TRINO, "Trino")
    probe_path: ClassVar[str] = "/v1/info"

    def validate_response(self, response: httpx.Response) -> str | None:
        body = _json_object(response)
        if body is None:
            return "response is not a JSON object"
        if body.get("starting") is True:
            return "coordinator still starting"
        return None


class IcebergRestCatalogAdapter(HttpProbeAdapter):
    """Iceberg REST catalog: ``GET /v1/config`` -> ``{"defaults": {...}, "overrides": {...}}``."""

    descriptor = _descriptor(EngineKind.ICEBERG_REST_CATALOG, "Iceberg REST Catalog")
    probe_path: ClassVar[str] = "/v1/config"

    def validate_response(self, response: httpx.Response) -> str | None:
        body = _json_object(response)
        if body is None or not {"defaults", "overrides"} <= body.keys():
            return "response is not an Iceberg catalog config"
        return None


class KafkaConnectAdapter(HttpProbeAdapter):
    """Kafka Connect (Debezium runtime): ``GET /`` -> ``{"version": ..., "commit": ...}``."""

    descriptor = _descriptor(EngineKind.KAFKA_CONNECT, "Kafka Connect")
    probe_path: ClassVar[str] = "/"

    def validate_response(self, response: httpx.Response) -> str | None:
        body = _json_object(response)
        if body is None or "version" not in body:
            return "response is not a Kafka Connect root document"
        return None


class FlinkAdapter(HttpProbeAdapter):
    """Flink JobManager REST: ``GET /overview`` -> cluster overview with ``taskmanagers``."""

    descriptor = _descriptor(EngineKind.FLINK, "Apache Flink")
    probe_path: ClassVar[str] = "/overview"

    def validate_response(self, response: httpx.Response) -> str | None:
        body = _json_object(response)
        if body is None or "taskmanagers" not in body:
            return "response is not a Flink cluster overview"
        if body.get("taskmanagers") == 0:
            return "no task managers registered"
        return None


class SparkMasterAdapter(HttpProbeAdapter):
    """Spark standalone master: ``GET /json/`` -> ``{"status": "ALIVE", ...}``."""

    descriptor = _descriptor(EngineKind.SPARK, "Apache Spark (standalone master)")
    probe_path: ClassVar[str] = "/json/"

    def validate_response(self, response: httpx.Response) -> str | None:
        body = _json_object(response)
        if body is None:
            return "response is not a JSON object"
        status = body.get("status")
        return None if status == "ALIVE" else f"master status is {status!r}"


class AirflowAdapter(HttpProbeAdapter):
    """Airflow: ``GET /health`` (override via option ``probe_path`` for other API versions)."""

    descriptor = _descriptor(EngineKind.AIRFLOW, "Apache Airflow")
    probe_path: ClassVar[str] = "/health"

    def validate_response(self, response: httpx.Response) -> str | None:
        body = _json_object(response)
        if body is None:
            return "response is not a JSON object"
        for component in ("metadatabase", "scheduler"):
            info = body.get(component)
            if isinstance(info, dict) and info.get("status") not in (None, "healthy"):
                return f"{component} is {info.get('status')}"
        return None


class OpenLineageAdapter(HttpProbeAdapter):
    """OpenLineage-compatible backend (Marquez): ``GET /api/v1/namespaces``."""

    descriptor = _descriptor(EngineKind.OPENLINEAGE, "OpenLineage backend (Marquez)")
    probe_path: ClassVar[str] = "/api/v1/namespaces"

    def validate_response(self, response: httpx.Response) -> str | None:
        body = _json_object(response)
        if body is None or "namespaces" not in body:
            return "response is not a namespaces listing"
        return None


class PrometheusAdapter(HttpProbeAdapter):
    """Prometheus: ``GET /-/healthy``."""

    descriptor = _descriptor(EngineKind.PROMETHEUS, "Prometheus")
    probe_path: ClassVar[str] = "/-/healthy"


class S3ObjectStoreAdapter(HttpProbeAdapter):
    """S3-compatible store with a MinIO-style liveness endpoint: ``GET /minio/health/live``.

    Other S3-compatible stores expose different liveness paths: set option ``probe_path``.
    """

    descriptor = _descriptor(EngineKind.OBJECT_STORE_S3, "S3-compatible object store")
    probe_path: ClassVar[str] = "/minio/health/live"


class KafkaAdapter(TcpProbeAdapter):
    """Kafka broker: TCP reachability ONLY (no protocol handshake). Weakest probe in the set."""

    descriptor = _descriptor(EngineKind.KAFKA, "Apache Kafka", ("health:tcp",))
    default_port: ClassVar[int] = 9092
