"""Response models of the Control Plane API as seen by SDK users.

``extra="ignore"``: the server may add fields in a minor version without breaking clients.
Removing/renaming a field is a breaking change caught by the OpenAPI contract tests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class PlatformInfo(_Model):
    name: str
    version: str
    environment: str
    git_sha: str


class Adapter(_Model):
    kind: str
    display_name: str
    maturity: str
    capabilities: list[str]
    contract_doc: str


class AcceptanceCriterion(_Model):
    id: str
    criterion: str
    status: str
    evidence: str | None = None


class Module(_Model):
    id: str
    title: str
    maturity: str
    summary: str
    responsibilities: list[str]
    public_interfaces: list[str]
    depends_on: list[str]
    engines: list[str]
    acceptance: list[AcceptanceCriterion]


class Connection(_Model):
    name: str
    kind: str
    endpoint: str
    secret_ref: str | None
    options: dict[str, str]
    created_at: datetime


class Health(_Model):
    state: str
    detail: str
    latency_ms: float | None
    checked_at: datetime


class ConnectionHealth(_Model):
    name: str
    kind: str
    maturity: str
    health: Health


class AuditEvent(_Model):
    occurred_at: datetime
    actor: str
    action: str
    target: str
    detail: dict[str, Any]
