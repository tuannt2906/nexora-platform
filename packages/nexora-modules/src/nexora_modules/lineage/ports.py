"""Public interfaces of the lineage module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexora_modules.lineage.models import RunEvent


@runtime_checkable
class LineageSink(Protocol):
    async def emit(self, event: RunEvent) -> None:
        """Deliver a run event. Delivering the same event twice must not corrupt the sink."""
        ...
