from __future__ import annotations

from collections.abc import Callable

import pytest
from pydantic import ValidationError

from nexora_core.errors import ConflictError, NotFoundError
from nexora_modules.streaming import StreamingPlatform, TopicSpec
from nexora_modules.streaming.fakes import InMemoryStreamingPlatform

PLATFORMS = [pytest.param(InMemoryStreamingPlatform, id="in-memory")]


@pytest.mark.contract
@pytest.mark.parametrize("factory", PLATFORMS)
async def test_create_list_describe(factory: Callable[[], StreamingPlatform]) -> None:
    platform = factory()
    assert isinstance(platform, StreamingPlatform)
    await platform.create_topic(TopicSpec(name="b.events", partitions=6))
    await platform.create_topic(TopicSpec(name="a.events", config={"retention.ms": "1000"}))
    assert await platform.list_topics() == ("a.events", "b.events")
    info = await platform.describe_topic("b.events")
    assert info.partitions == 6
    assert (await platform.describe_topic("a.events")).config == {"retention.ms": "1000"}


@pytest.mark.contract
@pytest.mark.parametrize("factory", PLATFORMS)
async def test_conflict_and_not_found(factory: Callable[[], StreamingPlatform]) -> None:
    platform = factory()
    await platform.create_topic(TopicSpec(name="t"))
    with pytest.raises(ConflictError):
        await platform.create_topic(TopicSpec(name="t"))
    with pytest.raises(NotFoundError):
        await platform.describe_topic("missing")


def test_spec_validation() -> None:
    with pytest.raises(ValidationError):
        TopicSpec(name="bad name!")
    with pytest.raises(ValidationError):
        TopicSpec(name="ok", partitions=0)
