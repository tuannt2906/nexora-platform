from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from nexora_modules.lineage import Dataset, EventType, Job, LineageSink, Run, RunEvent
from nexora_modules.lineage.fakes import InMemoryLineageSink

RUN_ID = UUID("11111111-1111-4111-8111-111111111111")
T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

SINKS = [pytest.param(InMemoryLineageSink, id="in-memory")]


def event(kind: EventType, offset: int = 0) -> RunEvent:
    return RunEvent(
        event_type=kind,
        event_time=T0 + timedelta(seconds=offset),
        run=Run(run_id=RUN_ID),
        job=Job(namespace="nexora", name="load_orders"),
        inputs=(Dataset(namespace="pg", name="public.orders"),),
        outputs=(Dataset(namespace="lake", name="sales.orders"),),
        producer="https://example.invalid/nexora/producer",
    )


def test_serialises_with_openlineage_names() -> None:
    dumped = event(EventType.START).model_dump(by_alias=True, mode="json")
    assert dumped["eventType"] == "START"
    assert dumped["run"] == {"runId": str(RUN_ID)}
    assert dumped["schemaURL"].startswith("https://openlineage.io/spec/")
    assert dumped["inputs"][0] == {"namespace": "pg", "name": "public.orders"}
    assert dumped["eventTime"].startswith("2026-01-01T12:00:00")


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(ValidationError):
        RunEvent(
            event_type=EventType.START,
            event_time=datetime(2026, 1, 1),  # noqa: DTZ001 - the point of the test
            run=Run(run_id=RUN_ID),
            job=Job(namespace="n", name="j"),
            producer="p",
        )


@pytest.mark.contract
@pytest.mark.parametrize("factory", SINKS)
async def test_emit_is_idempotent_and_builds_edges(factory: Callable[[], LineageSink]) -> None:
    sink = factory()
    assert isinstance(sink, LineageSink)
    start, done = event(EventType.START), event(EventType.COMPLETE, 5)
    for e in (start, start, done, done):
        await sink.emit(e)
    assert [e.event_type for e in sink.events] == [EventType.START, EventType.COMPLETE]  # type: ignore[attr-defined]
    assert sink.edges() == {("pg/public.orders", "lake/sales.orders")}  # type: ignore[attr-defined]
