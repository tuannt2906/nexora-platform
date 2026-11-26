"""In-memory reference implementation (deterministic, no I/O)."""

from __future__ import annotations

from nexora_core.errors import NotFoundError
from nexora_modules.cdc.models import CdcConnectorSpec, ConnectorState, ConnectorStatus


class InMemoryCdcConnectorManager:
    def __init__(self) -> None:
        self._specs: dict[str, CdcConnectorSpec] = {}

    async def deploy(self, spec: CdcConnectorSpec) -> ConnectorStatus:
        self._specs[spec.name] = spec
        return await self.status(spec.name)

    async def status(self, name: str) -> ConnectorStatus:
        spec = self._specs.get(name)
        if spec is None:
            raise NotFoundError(f"unknown connector '{name}'")
        return ConnectorStatus(
            name=spec.name, state=ConnectorState.RUNNING, tasks_running=len(spec.tables)
        )

    async def remove(self, name: str) -> None:
        if self._specs.pop(name, None) is None:
            raise NotFoundError(f"unknown connector '{name}'")
