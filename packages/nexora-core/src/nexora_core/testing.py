"""Reusable contract assertions for engine adapters.

Any adapter -- a fake, a probe against a mocked protocol, or (later) a real integration run
in CI -- must pass :func:`assert_adapter_contract`. Domain-port contract suites live next to
each module (``nexora_modules.<module>`` tests) and follow the same pattern.
"""

from __future__ import annotations

from nexora_core.engines import EngineAdapter, HealthReport, HealthState, Maturity


async def assert_adapter_contract(adapter: EngineAdapter) -> HealthReport:
    """Invariants every :class:`EngineAdapter` must uphold."""
    descriptor = adapter.descriptor
    assert descriptor.display_name, "descriptor must have a display name"
    assert descriptor.contract_doc.startswith("contracts/adapters/"), (
        "descriptor.contract_doc must point at contracts/adapters/<engine>.md"
    )
    assert isinstance(descriptor.maturity, Maturity)
    assert adapter.connection.kind == descriptor.kind

    report = await adapter.health()  # MUST NOT raise, even for unreachable engines
    assert isinstance(report, HealthReport)
    assert isinstance(report.state, HealthState)
    if report.latency_ms is not None:
        assert report.latency_ms >= 0
    assert report.checked_at.tzinfo is not None, "timestamps must be timezone-aware"
    await adapter.aclose()
    await adapter.aclose()  # aclose must be idempotent
    return report
