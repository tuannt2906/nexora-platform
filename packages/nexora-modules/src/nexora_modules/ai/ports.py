"""Public interfaces of the AI module."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from nexora_modules.ai.models import Completion, CompletionRequest, Embedding


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def embed(self, texts: Sequence[str]) -> tuple[Embedding, ...]:
        """One embedding per input text, same order, same dimensionality.

        Raises ValidationFailedError when any text is blank.
        """
        ...


@runtime_checkable
class LlmGateway(Protocol):
    async def complete(self, request: CompletionRequest) -> Completion:
        """Generate text. ``output_tokens`` never exceeds ``request.max_tokens``;
        ``finish_reason`` is LENGTH exactly when the output was cut at the limit."""
        ...
