from __future__ import annotations

from collections.abc import Callable

import pytest

from nexora_core.errors import ConflictError, NotFoundError
from nexora_modules.processing import JobPhase, ProcessingEngine, ProcessingJobSpec
from nexora_modules.processing.fakes import InMemoryProcessingEngine

ENGINES = [pytest.param(InMemoryProcessingEngine, id="in-memory")]


def spec(*, streaming: bool) -> ProcessingJobSpec:
    return ProcessingJobSpec(
        name="j", artifact_ref="registry.example/job:1.0.0", streaming=streaming
    )


@pytest.mark.contract
@pytest.mark.parametrize("factory", ENGINES)
async def test_batch_finishes_streaming_runs_until_canceled(
    factory: Callable[[], ProcessingEngine],
) -> None:
    engine = factory()
    assert isinstance(engine, ProcessingEngine)
    batch = await engine.submit_job(spec(streaming=False))
    assert batch.phase is JobPhase.FINISHED
    stream = await engine.submit_job(spec(streaming=True))
    assert (await engine.job_status(stream.job_id)).phase is JobPhase.RUNNING
    assert (await engine.cancel(stream.job_id)).phase is JobPhase.CANCELED


@pytest.mark.contract
@pytest.mark.parametrize("factory", ENGINES)
async def test_cancel_errors(factory: Callable[[], ProcessingEngine]) -> None:
    engine = factory()
    with pytest.raises(NotFoundError):
        await engine.cancel("nope")
    with pytest.raises(NotFoundError):
        await engine.job_status("nope")
    done = await engine.submit_job(spec(streaming=False))
    with pytest.raises(ConflictError):
        await engine.cancel(done.job_id)


def test_terminal_phases() -> None:
    assert JobPhase.FINISHED.is_terminal
    assert JobPhase.FAILED.is_terminal
    assert not JobPhase.RUNNING.is_terminal
    assert not JobPhase.SUBMITTED.is_terminal
