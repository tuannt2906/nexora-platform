"""Public interfaces of the orchestration module."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from nexora_modules.orchestration.models import RunInfo, WorkflowInfo


@runtime_checkable
class Orchestrator(Protocol):
    async def list_workflows(self) -> tuple[WorkflowInfo, ...]:
        """Known workflows, sorted by id."""
        ...

    async def trigger(self, workflow_id: str, conf: Mapping[str, str]) -> RunInfo:
        """Start a run. Raises NotFoundError for an unknown workflow."""
        ...

    async def run_status(self, run_id: str) -> RunInfo:
        """Raises NotFoundError for an unknown run."""
        ...
