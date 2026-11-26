"""Data types crossing the streaming port boundary."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

TOPIC_NAME_PATTERN = r"^[a-zA-Z0-9._-]{1,249}$"


class TopicSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=TOPIC_NAME_PATTERN)
    partitions: int = Field(default=3, ge=1, le=10_000)
    replication_factor: int = Field(default=1, ge=1, le=10)
    config: Mapping[str, str] = Field(default_factory=dict)


class TopicInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    partitions: int
    replication_factor: int
    config: Mapping[str, str] = Field(default_factory=dict)
