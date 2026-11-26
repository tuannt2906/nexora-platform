"""Public interfaces of the CDC module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexora_modules.cdc.models import CdcConnectorSpec, ConnectorStatus


@runtime_checkable
class CdcConnectorManager(Protocol):
    async def deploy(self, spec: CdcConnectorSpec) -> ConnectorStatus:
        """Create the connector, or update it when the name already exists (idempotent)."""
        ...

    async def status(self, name: str) -> ConnectorStatus:
        """Raises NotFoundError for an unknown connector."""
        ...

    async def remove(self, name: str) -> None:
        """Raises NotFoundError for an unknown connector."""
        ...
