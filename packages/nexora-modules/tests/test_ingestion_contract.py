from __future__ import annotations

from collections.abc import Callable

import pytest

from nexora_core.errors import NotFoundError
from nexora_modules.ingestion import (
    ColumnSchema,
    IngestionJobRunner,
    IngestionJobSpec,
    IngestionSource,
    JobState,
    SourceSchema,
)
from nexora_modules.ingestion.fakes import InMemoryIngestionSource, InMemoryJobRunner

ROWS = [{"id": i, "name": f"n{i}"} for i in range(25)]
SCHEMA = SourceSchema(columns=(ColumnSchema(name="id", type="int64", nullable=False),))


def make_source() -> IngestionSource:
    return InMemoryIngestionSource(SCHEMA, ROWS)


def make_runner() -> IngestionJobRunner:
    return InMemoryJobRunner({"src": make_source()})


SOURCES = [pytest.param(make_source, id="in-memory")]
RUNNERS = [pytest.param(make_runner, id="in-memory")]


@pytest.mark.contract
@pytest.mark.parametrize("factory", SOURCES)
async def test_source_pages_to_exhaustion(factory: Callable[[], IngestionSource]) -> None:
    source = factory()
    assert isinstance(source, IngestionSource)
    assert (await source.describe_schema()).columns[0].name == "id"
    seen: list[object] = []
    cursor = None
    while True:
        batch = await source.read_batch(cursor, 10)
        assert len(batch.rows) <= 10
        seen.extend(r["id"] for r in batch.rows)
        cursor = batch.next_cursor
        if cursor is None:
            break
    assert seen == list(range(25))


@pytest.mark.contract
@pytest.mark.parametrize("factory", RUNNERS)
async def test_runner_runs_and_reports(factory: Callable[[], IngestionJobRunner]) -> None:
    runner = factory()
    assert isinstance(runner, IngestionJobRunner)
    job_id = await runner.submit(IngestionJobSpec(source="src", target="t", batch_size=7))
    status = await runner.status(job_id)
    assert status.state is JobState.SUCCEEDED
    assert status.rows_written == 25


@pytest.mark.contract
@pytest.mark.parametrize("factory", RUNNERS)
async def test_runner_rejects_unknown(factory: Callable[[], IngestionJobRunner]) -> None:
    runner = factory()
    with pytest.raises(NotFoundError):
        await runner.submit(IngestionJobSpec(source="nope", target="t"))
    with pytest.raises(NotFoundError):
        await runner.status("job-999")
