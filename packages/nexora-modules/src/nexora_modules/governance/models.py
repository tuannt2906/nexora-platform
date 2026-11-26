"""Data types crossing the governance port boundary."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class PolicyRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str = Field(min_length=1, description="Authenticated principal id")
    action: str = Field(min_length=1, description="e.g. read, write, admin")
    resource: str = Field(min_length=1, description="e.g. table:sales.orders")


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: bool
    reason: str


class AuditRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    action: str
    resource: str
    allowed: bool
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
