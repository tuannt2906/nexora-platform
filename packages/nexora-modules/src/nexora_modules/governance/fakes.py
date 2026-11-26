"""In-memory reference implementations (deterministic, no I/O)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from nexora_modules.governance.models import AuditRecord, Decision, PolicyRequest


@dataclass(frozen=True)
class AllowRule:
    """Grant ``subject`` the ``action`` on every resource starting with ``resource_prefix``."""

    subject: str
    action: str
    resource_prefix: str


class RuleBasedPolicyDecisionPoint:
    """Default-deny allow-list evaluator."""

    def __init__(self, rules: Iterable[AllowRule]) -> None:
        self._rules = tuple(rules)

    async def decide(self, request: PolicyRequest) -> Decision:
        for rule in self._rules:
            if (
                rule.subject == request.subject
                and rule.action == request.action
                and request.resource.startswith(rule.resource_prefix)
            ):
                return Decision(allowed=True, reason=f"allowed by rule on '{rule.resource_prefix}'")
        return Decision(allowed=False, reason="no matching allow rule (default deny)")


class InMemoryAuditSink:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    async def record(self, record: AuditRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)
