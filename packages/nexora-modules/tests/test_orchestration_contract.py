from __future__ import annotations

from collections.abc import Callable

import pytest

from nexora_core.errors import NotFoundError
from nexora_modules.orchestration import Orchestrator, RunState, WorkflowInfo
from nexora_modules.orchestration.fakes import InMemoryOrchestrator


def make_orchestrator() -> Orchestrator:
    return InMemoryOrchestrator(
        [WorkflowInfo(workflow_id="b_load"), WorkflowInfo(workflow_id="a_load", description="d")]
    )


ORCHESTRATORS = [pytest.param(make_orchestrator, id="in-memory")]


@pytest.mark.contract
@pytest.mark.parametrize("factory", ORCHESTRATORS)
async def test_list_trigger_status(factory: Callable[[], Orchestrator]) -> None:
    orchestrator = factory()
    assert isinstance(orchestrator, Orchestrator)
    assert [w.workflow_id for w in await orchestrator.list_workflows()] == ["a_load", "b_load"]
    run = await orchestrator.trigger("a_load", {"date": "2026-01-01"})
    assert run.state is RunState.SUCCESS
    again = await orchestrator.run_status(run.run_id)
    assert again.conf == {"date": "2026-01-01"}


@pytest.mark.contract
@pytest.mark.parametrize("factory", ORCHESTRATORS)
async def test_not_found(factory: Callable[[], Orchestrator]) -> None:
    orchestrator = factory()
    with pytest.raises(NotFoundError):
        await orchestrator.trigger("nope", {})
    with pytest.raises(NotFoundError):
        await orchestrator.run_status("run-999")
