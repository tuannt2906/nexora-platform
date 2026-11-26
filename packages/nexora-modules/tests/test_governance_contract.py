from __future__ import annotations

from collections.abc import Callable

import pytest

from nexora_modules.governance import (
    AuditRecord,
    AuditSink,
    PolicyDecisionPoint,
    PolicyRequest,
)
from nexora_modules.governance.fakes import (
    AllowRule,
    InMemoryAuditSink,
    RuleBasedPolicyDecisionPoint,
)


def make_pdp() -> PolicyDecisionPoint:
    return RuleBasedPolicyDecisionPoint([AllowRule("alice", "read", "table:sales.")])


PDPS = [pytest.param(make_pdp, id="rule-based")]
SINKS = [pytest.param(InMemoryAuditSink, id="in-memory")]


@pytest.mark.contract
@pytest.mark.parametrize("factory", PDPS)
async def test_default_deny_and_allow(factory: Callable[[], PolicyDecisionPoint]) -> None:
    pdp = factory()
    assert isinstance(pdp, PolicyDecisionPoint)
    allowed = await pdp.decide(
        PolicyRequest(subject="alice", action="read", resource="table:sales.orders")
    )
    assert allowed.allowed
    for subject, action, resource in [
        ("bob", "read", "table:sales.orders"),
        ("alice", "write", "table:sales.orders"),
        ("alice", "read", "table:hr.people"),
    ]:
        decision = await pdp.decide(
            PolicyRequest(subject=subject, action=action, resource=resource)
        )
        assert not decision.allowed
        assert "default deny" in decision.reason


@pytest.mark.contract
@pytest.mark.parametrize("factory", SINKS)
async def test_audit_sink_appends_in_order(factory: Callable[[], AuditSink]) -> None:
    sink = factory()
    assert isinstance(sink, AuditSink)
    await sink.record(AuditRecord(subject="a", action="read", resource="r1", allowed=True))
    await sink.record(AuditRecord(subject="b", action="read", resource="r2", allowed=False))
    records = sink.records  # type: ignore[attr-defined]
    assert [r.resource for r in records] == ["r1", "r2"]
    assert all(r.occurred_at.tzinfo is not None for r in records)
