from __future__ import annotations

import pytest
from pydantic import ValidationError

from nexora_core.engines import (
    AdapterRegistry,
    ConnectionSpec,
    EngineAdapter,
    EngineDescriptor,
    EngineKind,
    HealthReport,
    HealthState,
    Maturity,
)
from nexora_core.errors import ConflictError, NotFoundError
from nexora_core.testing import assert_adapter_contract


class FakeAdapter(EngineAdapter):
    descriptor = EngineDescriptor(
        kind=EngineKind.TRINO,
        display_name="Fake",
        maturity=Maturity.CONTRACT,
        contract_doc="contracts/adapters/trino.md",
    )

    async def health(self) -> HealthReport:
        return HealthReport(state=HealthState.HEALTHY, latency_ms=1.0)


def spec(kind: EngineKind = EngineKind.TRINO, name: str = "main") -> ConnectionSpec:
    return ConnectionSpec(kind=kind, name=name, endpoint="http://x:1")


def test_registry_creates_adapter_for_kind() -> None:
    registry = AdapterRegistry()
    registry.register(FakeAdapter.descriptor, FakeAdapter)
    assert isinstance(registry.create(spec()), FakeAdapter)
    assert registry.descriptor(EngineKind.TRINO).display_name == "Fake"
    assert registry.descriptors() == [FakeAdapter.descriptor]


def test_registry_rejects_duplicates_and_unknown_kinds() -> None:
    registry = AdapterRegistry()
    registry.register(FakeAdapter.descriptor, FakeAdapter)
    with pytest.raises(ConflictError):
        registry.register(FakeAdapter.descriptor, FakeAdapter)
    with pytest.raises(NotFoundError):
        registry.descriptor(EngineKind.FLINK)
    with pytest.raises(NotFoundError):
        registry.create(spec(EngineKind.FLINK))


def test_adapter_refuses_foreign_connection_kind() -> None:
    with pytest.raises(ValueError, match="handles"):
        FakeAdapter(spec(EngineKind.FLINK))


@pytest.mark.parametrize("name", ["", "Upper", "-lead", "trail-", "a" * 64, "has space"])
def test_connection_name_validation(name: str) -> None:
    with pytest.raises(ValidationError):
        ConnectionSpec(kind=EngineKind.TRINO, name=name, endpoint="http://x")


def test_maturity_vocabulary_is_stable() -> None:
    # Changing these values is a breaking API/contract change (see ADR-0004).
    assert [m.value for m in Maturity] == [
        "planned",
        "contract",
        "probe",
        "functional",
        "production",
    ]


async def test_contract_helper_accepts_conforming_adapter() -> None:
    report = await assert_adapter_contract(FakeAdapter(spec()))
    assert report.state is HealthState.HEALTHY
