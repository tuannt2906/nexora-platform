"""OpenLineage-style run event model.

Field names serialise with the OpenLineage camelCase aliases (``eventType``, ``runId`` ...)
via ``model_dump(by_alias=True, mode="json")``. Conformance with a live OpenLineage backend
is NOT verified yet (see module.toml, LIN-3).
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_URL = "https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent"


class EventType(enum.StrEnum):
    START = "START"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    ABORT = "ABORT"
    FAIL = "FAIL"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)


class Run(_Frozen):
    run_id: UUID = Field(alias="runId")


class Job(_Frozen):
    namespace: str = Field(min_length=1)
    name: str = Field(min_length=1)


class Dataset(_Frozen):
    namespace: str = Field(min_length=1)
    name: str = Field(min_length=1)


class RunEvent(_Frozen):
    event_type: EventType = Field(alias="eventType")
    event_time: datetime = Field(alias="eventTime")
    run: Run
    job: Job
    inputs: tuple[Dataset, ...] = ()
    outputs: tuple[Dataset, ...] = ()
    producer: str = Field(min_length=1, description="URI identifying the emitting software")
    schema_url: str = Field(default=SCHEMA_URL, alias="schemaURL")

    @field_validator("event_time")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        return value
