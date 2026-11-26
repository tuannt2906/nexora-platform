"""Public interfaces of the governance module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexora_modules.governance.models import AuditRecord, Decision, PolicyRequest


@runtime_checkable
class PolicyDecisionPoint(Protocol):
    async def decide(self, request: PolicyRequest) -> Decision:
        """Authorise a request. Implementations MUST default to deny."""
        ...


@runtime_checkable
class AuditSink(Protocol):
    async def record(self, record: AuditRecord) -> None:
        """Append an audit record. Records are never modified or deleted through this port."""
        ...
