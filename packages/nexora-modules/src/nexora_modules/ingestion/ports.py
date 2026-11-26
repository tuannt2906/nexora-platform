"""Public interfaces of the ingestion module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexora_modules.ingestion.models import Batch, IngestionJobSpec, JobStatus, SourceSchema


@runtime_checkable
class IngestionSource(Protocol):
    """A readable, pageable data source."""

    async def describe_schema(self) -> SourceSchema:
        """Return the source schema."""
        ...

    async def read_batch(self, cursor: str | None, limit: int) -> Batch:
        """Read up to ``limit`` rows after ``cursor`` (None = from the start)."""
        ...


@runtime_checkable
class IngestionJobRunner(Protocol):
    """Runs ingestion jobs. Implementations may be asynchronous engines."""

    async def submit(self, spec: IngestionJobSpec) -> str:
        """Start a job; returns its id. Raises NotFoundError for an unknown source."""
        ...

    async def status(self, job_id: str) -> JobStatus:
        """Raises NotFoundError for an unknown job id."""
        ...
