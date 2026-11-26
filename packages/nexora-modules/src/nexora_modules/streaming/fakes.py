"""In-memory reference implementation (deterministic, no I/O)."""

from __future__ import annotations

from nexora_core.errors import ConflictError, NotFoundError
from nexora_modules.streaming.models import TopicInfo, TopicSpec


class InMemoryStreamingPlatform:
    def __init__(self) -> None:
        self._topics: dict[str, TopicInfo] = {}

    async def list_topics(self) -> tuple[str, ...]:
        return tuple(sorted(self._topics))

    async def create_topic(self, spec: TopicSpec) -> TopicInfo:
        if spec.name in self._topics:
            raise ConflictError(f"topic '{spec.name}' already exists")
        info = TopicInfo(
            name=spec.name,
            partitions=spec.partitions,
            replication_factor=spec.replication_factor,
            config=dict(spec.config),
        )
        self._topics[spec.name] = info
        return info

    async def describe_topic(self, name: str) -> TopicInfo:
        try:
            return self._topics[name]
        except KeyError:
            raise NotFoundError(f"unknown topic '{name}'") from None
