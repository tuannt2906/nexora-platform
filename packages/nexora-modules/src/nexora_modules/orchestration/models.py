"""Data types crossing the orchestration port boundary."""

from __future__ import annotations

import enum
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field


class RunState(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class WorkflowInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow_id: str = Field(min_length=1)
    description: str = ""


class RunInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    workflow_id: str
    state: RunState
    conf: Mapping[str, str] = Field(default_factory=dict)
