"""Data types crossing the query port boundary."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    sql: str = Field(min_length=1, max_length=100_000)
    max_rows: int = Field(default=1000, ge=1, le=1_000_000)


class QueryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    truncated: bool = False
