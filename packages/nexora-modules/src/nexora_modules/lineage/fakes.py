"""In-memory reference implementation (deterministic, no I/O)."""

from __future__ import annotations

from nexora_modules.lineage.models import EventType, RunEvent


class InMemoryLineageSink:
    """Keeps events de-duplicated by (run, type, time) so redelivery is harmless."""

    def __init__(self) -> None:
        self._events: dict[tuple[str, str, str], RunEvent] = {}

    async def emit(self, event: RunEvent) -> None:
        key = (str(event.run.run_id), event.event_type.value, event.event_time.isoformat())
        self._events.setdefault(key, event)

    @property
    def events(self) -> tuple[RunEvent, ...]:
        return tuple(sorted(self._events.values(), key=lambda e: e.event_time))

    def edges(self) -> set[tuple[str, str]]:
        """Dataset-level edges ``input -> output`` from COMPLETE events."""
        return {
            (f"{i.namespace}/{i.name}", f"{o.namespace}/{o.name}")
            for e in self.events
            if e.event_type is EventType.COMPLETE
            for i in e.inputs
            for o in e.outputs
        }
