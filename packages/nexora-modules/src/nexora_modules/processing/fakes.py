"""In-memory reference implementation (deterministic, no I/O)."""

from __future__ import annotations

from nexora_core.errors import ConflictError, NotFoundError
from nexora_modules.processing.models import JobInfo, JobPhase, ProcessingJobSpec


class InMemoryProcessingEngine:
    """Streaming jobs stay RUNNING until canceled; batch jobs finish immediately."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobInfo] = {}

    async def submit_job(self, spec: ProcessingJobSpec) -> JobInfo:
        job_id = f"job-{len(self._jobs) + 1}"
        phase = JobPhase.RUNNING if spec.streaming else JobPhase.FINISHED
        info = JobInfo(job_id=job_id, name=spec.name, phase=phase)
        self._jobs[job_id] = info
        return info

    async def job_status(self, job_id: str) -> JobInfo:
        try:
            return self._jobs[job_id]
        except KeyError:
            raise NotFoundError(f"unknown job '{job_id}'") from None

    async def cancel(self, job_id: str) -> JobInfo:
        current = await self.job_status(job_id)
        if current.phase.is_terminal:
            raise ConflictError(f"job '{job_id}' is already {current.phase.value}")
        canceled = current.model_copy(update={"phase": JobPhase.CANCELED})
        self._jobs[job_id] = canceled
        return canceled
