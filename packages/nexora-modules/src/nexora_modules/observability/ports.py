"""Public interfaces of the observability module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexora_modules.observability.models import InstantQueryResult


@runtime_checkable
class MetricsQuery(Protocol):
    async def instant_query(self, promql: str) -> InstantQueryResult:
        """Evaluate a PromQL expression at the current instant.

        Raises ValidationFailedError for an empty or unparsable expression. A well-formed
        selector that matches nothing returns an empty result (Prometheus semantics).
        """
        ...
