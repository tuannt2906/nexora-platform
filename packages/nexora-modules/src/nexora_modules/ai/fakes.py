"""Deterministic fakes. They contain NO model: vectors are hash-derived, text is an echo."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from nexora_core.errors import ValidationFailedError
from nexora_modules.ai.models import Completion, CompletionRequest, Embedding, FinishReason

FAKE_MODEL = "fake-deterministic-v1"


class HashEmbeddingProvider:
    def __init__(self, dimensions: int = 8) -> None:
        if not 1 <= dimensions <= 32:
            raise ValueError("dimensions must be between 1 and 32")
        self._dimensions = dimensions

    async def embed(self, texts: Sequence[str]) -> tuple[Embedding, ...]:
        if any(not t.strip() for t in texts):
            raise ValidationFailedError("cannot embed blank text")
        out = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vector = tuple(digest[i] / 255.0 for i in range(self._dimensions))
            out.append(Embedding(model=FAKE_MODEL, vector=vector))
        return tuple(out)


class EchoLlmGateway:
    """Echoes the prompt words (one word == one token) up to ``max_tokens``."""

    async def complete(self, request: CompletionRequest) -> Completion:
        words = request.prompt.split()
        kept = words[: request.max_tokens]
        truncated = len(words) > request.max_tokens
        return Completion(
            model=FAKE_MODEL,
            text=" ".join(kept),
            finish_reason=FinishReason.LENGTH if truncated else FinishReason.STOP,
            input_tokens=len(words),
            output_tokens=len(kept),
        )
