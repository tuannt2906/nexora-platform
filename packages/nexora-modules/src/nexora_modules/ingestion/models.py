"""Data types crossing the ingestion port boundary."""

from __future__ import annotations

import enum
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ColumnSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    type: str = Field(min_length=1, description="Source-neutral type name, e.g. string, int64")
    nullable: bool = True


class SourceSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    columns: tuple[ColumnSchema, ...]


class Batch(BaseModel):
    """One page of rows. ``next_cursor`` is None when the source is exhausted."""

    model_config = ConfigDict(frozen=True)

    rows: tuple[Mapping[str, Any], ...]
    next_cursor: str | None = None


class JobState(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IngestionJobSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    batch_size: int = Field(default=1000, ge=1, le=100_000)


class JobStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str
    state: JobState
    rows_written: int = Field(default=0, ge=0)
    error: str | None = None
