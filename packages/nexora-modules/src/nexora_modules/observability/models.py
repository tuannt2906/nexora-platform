"""Data types crossing the observability port boundary."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field


class MetricSample(BaseModel):
    model_config = ConfigDict(frozen=True)

    labels: Mapping[str, str] = Field(default_factory=dict)
    value: float
    timestamp: float = Field(description="Unix seconds")


class InstantQueryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    samples: tuple[MetricSample, ...]
