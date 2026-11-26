"""Engine adapters. Only the Control Plane (and tests) may import this package."""

from __future__ import annotations

from nexora_core.engines import AdapterRegistry
from nexora_modules.adapters.probes import (
    AirflowAdapter,
    FlinkAdapter,
    IcebergRestCatalogAdapter,
    KafkaAdapter,
    KafkaConnectAdapter,
    OpenLineageAdapter,
    PrometheusAdapter,
    S3ObjectStoreAdapter,
    SparkMasterAdapter,
    TrinoAdapter,
)

ADAPTER_CLASSES = (
    KafkaAdapter,
    KafkaConnectAdapter,
    FlinkAdapter,
    SparkMasterAdapter,
    IcebergRestCatalogAdapter,
    S3ObjectStoreAdapter,
    TrinoAdapter,
    AirflowAdapter,
    OpenLineageAdapter,
    PrometheusAdapter,
)


def default_registry() -> AdapterRegistry:
    """Registry with every adapter shipped in this release."""
    registry = AdapterRegistry()
    for cls in ADAPTER_CLASSES:
        registry.register(cls.descriptor, cls)
    return registry


__all__ = ["ADAPTER_CLASSES", "default_registry"]
