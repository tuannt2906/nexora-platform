"""Public API schemas (the HTTP contract). Changing these changes contracts/openapi/*.json."""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nexora_core.engines import ConnectionSpec, EngineKind, HealthReport

_BLOCKED_HOSTS = {"metadata.google.internal", "metadata"}
_NAME_RE = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"
# Absolute path only: no authority/userinfo tricks (`@`), query, fragment or whitespace.
PROBE_PATH_RE = re.compile(r"^/(?!/)[A-Za-z0-9._~%:/-]*$")


def validate_endpoint(endpoint: str) -> str:
    """Reject endpoints the control plane must never probe (SSRF hardening).

    Only plain ``host:port`` and ``http(s)://`` endpoints are accepted; link-local/metadata
    addresses are blocked. Private addresses and cluster-internal DNS names ARE allowed,
    because engines legitimately live there; access is already gated by the API token.
    """
    value = endpoint.strip()
    if "://" in value:
        scheme = value.split("://", 1)[0].lower()
        if scheme not in {"http", "https"}:
            raise ValueError("endpoint scheme must be http or https")
        parsed = urlparse(value)
        if parsed.username or parsed.password:
            raise ValueError("credentials in the endpoint are not allowed; use secret_ref")
        host = parsed.hostname
    else:
        if not re.match(r"^[A-Za-z0-9.-]+(:\d{1,5})?(,[A-Za-z0-9.-]+(:\d{1,5})?)*$", value):
            raise ValueError("endpoint must be host[:port] or an http(s) URL")
        host = value.split(",")[0].split(":")[0]
    if not host:
        raise ValueError("endpoint has no host")
    if host.lower() in _BLOCKED_HOSTS:
        raise ValueError("endpoint host is not allowed")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return value
    if ip.is_link_local or ip.is_unspecified or ip.is_multicast:
        raise ValueError("endpoint address is not allowed")
    return value


class PlatformInfo(BaseModel):
    name: str
    version: str
    environment: str
    git_sha: str


class AdapterInfo(BaseModel):
    kind: EngineKind
    display_name: str
    maturity: str
    capabilities: list[str]
    contract_doc: str


class ConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EngineKind
    name: str = Field(min_length=1, max_length=63, pattern=_NAME_RE)
    endpoint: str = Field(min_length=1, max_length=2048)
    secret_ref: str | None = Field(
        default=None,
        max_length=512,
        description="Opaque reference to a secret in the external secret manager. Never a secret.",
    )
    options: dict[str, str] = Field(default_factory=dict, max_length=32)

    @field_validator("endpoint")
    @classmethod
    def _endpoint(cls, value: str) -> str:
        return validate_endpoint(value)

    @field_validator("options")
    @classmethod
    def _options(cls, value: dict[str, str]) -> dict[str, str]:
        probe_path = value.get("probe_path")
        if probe_path is not None and not PROBE_PATH_RE.match(probe_path):
            raise ValueError("options.probe_path must be an absolute path such as /health")
        return value

    def to_spec(self) -> ConnectionSpec:
        return ConnectionSpec(
            kind=self.kind,
            name=self.name,
            endpoint=self.endpoint,
            secret_ref=self.secret_ref,
            options=self.options,
        )


class ConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    kind: EngineKind
    endpoint: str
    secret_ref: str | None
    options: dict[str, str]
    created_at: datetime


class ConnectionHealth(BaseModel):
    name: str
    kind: EngineKind
    maturity: str
    health: HealthReport


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    occurred_at: datetime
    actor: str
    action: str
    target: str
    detail: dict[str, Any]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorBody
