"""Public interfaces of the processing module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexora_modules.processing.models import JobInfo, ProcessingJobSpec


@runtime_checkable
class ProcessingEngine(Protocol):
    async def submit_job(self, spec: ProcessingJobSpec) -> JobInfo:
        """Submit a job; the returned phase is SUBMITTED or later."""
        ...

    async def job_status(self, job_id: str) -> JobInfo:
        """Raises NotFoundError for an unknown job."""
        ...

    async def cancel(self, job_id: str) -> JobInfo:
        """Cancel a job. NotFoundError if unknown; ConflictError if already terminal."""
        ...
