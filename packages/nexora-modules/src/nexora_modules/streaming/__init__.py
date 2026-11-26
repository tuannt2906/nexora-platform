"""Streaming platform: topic management on Kafka-compatible brokers."""

from nexora_modules.streaming.models import TopicInfo, TopicSpec
from nexora_modules.streaming.ports import StreamingPlatform

__all__ = ["StreamingPlatform", "TopicInfo", "TopicSpec"]
