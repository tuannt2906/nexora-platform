"""Public interfaces of the streaming module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexora_modules.streaming.models import TopicInfo, TopicSpec


@runtime_checkable
class StreamingPlatform(Protocol):
    async def list_topics(self) -> tuple[str, ...]:
        """Topic names, sorted ascending."""
        ...

    async def create_topic(self, spec: TopicSpec) -> TopicInfo:
        """Raises ConflictError when the topic already exists."""
        ...

    async def describe_topic(self, name: str) -> TopicInfo:
        """Raises NotFoundError for an unknown topic."""
        ...
