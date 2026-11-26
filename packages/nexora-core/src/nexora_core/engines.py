"""Engine-adapter contract.

Every third-party engine (Kafka, Flink, Spark, Trino, Iceberg catalog, ...) is reached
through an :class:`EngineAdapter`. Domain modules never import an engine client library
directly; they depend on ports (see ``nexora_modules.<module>.ports``) and the Control
Plane wires adapters in at runtime.

Honesty rule: every adapter declares a :class:`Maturity`. A configuration file or a
Docker image existing does NOT raise maturity -- only verified behaviour does.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from nexora_core.errors import ConflictError, NotFoundError


class EngineKind(enum.StrEnum):
    """Stable identifiers of supported engine types. Adding a value is an ADR-worthy change."""

    KAFKA = "kafka"
    KAFKA_CONNECT = "kafka-connect"  # Debezium CDC runs on Kafka Connect
    FLINK = "flink"
    SPARK = "spark"
    ICEBERG_REST_CATALOG = "iceberg-rest-catalog"
    OBJECT_STORE_S3 = "object-store-s3"
    TRINO = "trino"
    AIRFLOW = "airflow"
    OPENLINEAGE = "openlineage"
    PROMETHEUS = "prometheus"


class Maturity(enum.StrEnum):
    """How much of an integration is actually verified. Ordered from weakest to strongest."""

    PLANNED = "planned"  # nothing implemented
    CONTRACT = "contract"  # port + fake + contract tests; no real engine involved
    PROBE = "probe"  # real adapter, health/capability probe only, verified against mock protocol
    FUNCTIONAL = "functional"  # implements the domain port, verified against a REAL engine in CI
    PRODUCTION = "production"  # functional + operated/observed on a production environment


class HealthState(enum.StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthReport(BaseModel):
    """Result of probing one engine endpoint. Never contains secrets."""

    model_config = ConfigDict(frozen=True)

    state: HealthState
    detail: str = ""
    latency_ms: float | None = Field(default=None, ge=0)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EngineDescriptor(BaseModel):
    """Static, documented facts about an adapter implementation."""

    model_config = ConfigDict(frozen=True)

    kind: EngineKind
    display_name: str
    maturity: Maturity
    capabilities: tuple[str, ...] = ()
    contract_doc: str = Field(description="Repo-relative path of the adapter contract document")


class ConnectionSpec(BaseModel):
    """Where an engine lives. Credentials are referenced, never embedded.

    ``secret_ref`` is an opaque pointer (e.g. ``k8s://nexora/trino-credentials``) that the
    runtime secret resolver understands. The Control Plane stores the reference only.
    """

    model_config = ConfigDict(frozen=True)

    kind: EngineKind
    name: str = Field(min_length=1, max_length=63, pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
    endpoint: str = Field(min_length=1, max_length=2048)
    secret_ref: str | None = Field(default=None, max_length=512)
    options: Mapping[str, str] = Field(default_factory=dict)


class EngineAdapter(ABC):
    """Port every engine integration implements."""

    descriptor: EngineDescriptor

    def __init__(self, connection: ConnectionSpec) -> None:
        if connection.kind != self.descriptor.kind:
            raise ValueError(
                f"{type(self).__name__} handles {self.descriptor.kind}, got {connection.kind}"
            )
        self.connection = connection

    @abstractmethod
    async def health(self) -> HealthReport:
        """Probe the engine. MUST NOT raise for an unreachable engine: report UNHEALTHY."""

    async def aclose(self) -> None:  # noqa: B027 - optional hook, default is a no-op
        """Release client resources."""


AdapterFactory = Callable[[ConnectionSpec], EngineAdapter]


class AdapterRegistry:
    """Maps :class:`EngineKind` to the adapter implementation that handles it."""

    def __init__(self) -> None:
        self._factories: dict[EngineKind, tuple[EngineDescriptor, AdapterFactory]] = {}

    def register(self, descriptor: EngineDescriptor, factory: AdapterFactory) -> None:
        if descriptor.kind in self._factories:
            raise ConflictError(f"adapter for {descriptor.kind} already registered")
        self._factories[descriptor.kind] = (descriptor, factory)

    def descriptors(self) -> list[EngineDescriptor]:
        return [d for d, _ in self._factories.values()]

    def descriptor(self, kind: EngineKind) -> EngineDescriptor:
        try:
            return self._factories[kind][0]
        except KeyError:
            raise NotFoundError(f"no adapter registered for engine kind '{kind}'") from None

    def create(self, connection: ConnectionSpec) -> EngineAdapter:
        try:
            _, factory = self._factories[connection.kind]
        except KeyError:
            raise NotFoundError(
                f"no adapter registered for engine kind '{connection.kind}'"
            ) from None
        return factory(connection)
