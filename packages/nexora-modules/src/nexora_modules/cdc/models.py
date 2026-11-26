"""Data types crossing the CDC port boundary."""

from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field


class ConnectorState(enum.StrEnum):
    """Mirrors Kafka Connect connector states."""

    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    UNASSIGNED = "unassigned"


class CdcConnectorSpec(BaseModel):
    """Desired state of one CDC connector. Credentials are referenced, never embedded."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", max_length=63)
    source_type: str = Field(min_length=1, description="e.g. postgres, mysql")
    connection_ref: str = Field(min_length=1, description="Opaque secret/connection reference")
    tables: tuple[str, ...] = Field(min_length=1, description="schema.table names to capture")
    topic_prefix: str = Field(min_length=1)


class ConnectorStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    state: ConnectorState
    tasks_running: int = Field(default=0, ge=0)
    error: str | None = None
