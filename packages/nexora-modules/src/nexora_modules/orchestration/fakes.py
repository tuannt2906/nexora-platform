"""In-memory reference implementation (deterministic, no I/O)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from nexora_core.errors import NotFoundError
from nexora_modules.orchestration.models import RunInfo, RunState, WorkflowInfo


class InMemoryOrchestrator:
    """Runs complete instantly with SUCCESS."""

    def __init__(self, workflows: Iterable[WorkflowInfo]) -> None:
        self._workflows = {w.workflow_id: w for w in workflows}
        self._runs: dict[str, RunInfo] = {}

    async def list_workflows(self) -> tuple[WorkflowInfo, ...]:
        return tuple(self._workflows[k] for k in sorted(self._workflows))

    async def trigger(self, workflow_id: str, conf: Mapping[str, str]) -> RunInfo:
        if workflow_id not in self._workflows:
            raise NotFoundError(f"unknown workflow '{workflow_id}'")
        run = RunInfo(
            run_id=f"run-{len(self._runs) + 1}",
            workflow_id=workflow_id,
            state=RunState.SUCCESS,
            conf=dict(conf),
        )
        self._runs[run.run_id] = run
        return run

    async def run_status(self, run_id: str) -> RunInfo:
        try:
            return self._runs[run_id]
        except KeyError:
            raise NotFoundError(f"unknown run '{run_id}'") from None
