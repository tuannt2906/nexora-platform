"""Data types crossing the AI port boundary."""

from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field


class FinishReason(enum.StrEnum):
    STOP = "stop"
    LENGTH = "length"


class Embedding(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: str
    vector: tuple[float, ...] = Field(min_length=1)


class CompletionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt: str = Field(min_length=1, max_length=200_000)
    max_tokens: int = Field(default=256, ge=1, le=100_000)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class Completion(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: str
    text: str
    finish_reason: FinishReason
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
