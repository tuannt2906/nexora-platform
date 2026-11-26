"""Data types crossing the processing port boundary."""

from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field


class JobPhase(enum.StrEnum):
    SUBMITTED = "submitted"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELED = "canceled"

    @property
    def is_terminal(self) -> bool:
        return self in (JobPhase.FINISHED, JobPhase.FAILED, JobPhase.CANCELED)


class ProcessingJobSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=128)
    artifact_ref: str = Field(min_length=1, description="Immutable artifact (image or jar) ref")
    args: tuple[str, ...] = ()
    streaming: bool = False


class JobInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str
    name: str
    phase: JobPhase
