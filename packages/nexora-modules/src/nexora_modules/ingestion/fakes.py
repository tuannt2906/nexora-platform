"""In-memory reference implementations (deterministic, no I/O)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nexora_core.errors import NotFoundError
from nexora_modules.ingestion.models import (
    Batch,
    IngestionJobSpec,
    JobState,
    JobStatus,
    SourceSchema,
)
from nexora_modules.ingestion.ports import IngestionSource


class InMemoryIngestionSource:
    def __init__(self, schema: SourceSchema, rows: Sequence[Mapping[str, Any]]) -> None:
        self._schema = schema
        self._rows = tuple(rows)

    async def describe_schema(self) -> SourceSchema:
        return self._schema

    async def read_batch(self, cursor: str | None, limit: int) -> Batch:
        start = int(cursor) if cursor else 0
        end = min(start + limit, len(self._rows))
        next_cursor = str(end) if end < len(self._rows) else None
        return Batch(rows=self._rows[start:end], next_cursor=next_cursor)


class InMemoryJobRunner:
    """Runs jobs synchronously at submit time; targets are dicts of row lists."""

    def __init__(self, sources: Mapping[str, IngestionSource]) -> None:
        self._sources = dict(sources)
        self._jobs: dict[str, JobStatus] = {}
        self.targets: dict[str, list[Mapping[str, Any]]] = {}

    async def submit(self, spec: IngestionJobSpec) -> str:
        source = self._sources.get(spec.source)
        if source is None:
            raise NotFoundError(f"unknown source '{spec.source}'")
        job_id = f"job-{len(self._jobs) + 1}"
        written = 0
        cursor: str | None = None
        sink = self.targets.setdefault(spec.target, [])
        while True:
            batch = await source.read_batch(cursor, spec.batch_size)
            sink.extend(batch.rows)
            written += len(batch.rows)
            cursor = batch.next_cursor
            if cursor is None:
                break
        self._jobs[job_id] = JobStatus(
            job_id=job_id, state=JobState.SUCCEEDED, rows_written=written
        )
        return job_id

    async def status(self, job_id: str) -> JobStatus:
        try:
            return self._jobs[job_id]
        except KeyError:
            raise NotFoundError(f"unknown job '{job_id}'") from None
