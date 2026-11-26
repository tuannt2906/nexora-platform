from __future__ import annotations

from collections.abc import Callable

import pytest
from pydantic import ValidationError

from nexora_core.errors import ValidationFailedError
from nexora_modules.ai import (
    CompletionRequest,
    EmbeddingProvider,
    FinishReason,
    LlmGateway,
)
from nexora_modules.ai.fakes import EchoLlmGateway, HashEmbeddingProvider

EMBEDDERS = [pytest.param(HashEmbeddingProvider, id="hash-fake")]
GATEWAYS = [pytest.param(EchoLlmGateway, id="echo-fake")]


@pytest.mark.contract
@pytest.mark.parametrize("factory", EMBEDDERS)
async def test_embeddings_order_and_dimension(factory: Callable[[], EmbeddingProvider]) -> None:
    provider = factory()
    assert isinstance(provider, EmbeddingProvider)
    result = await provider.embed(["alpha", "beta", "alpha"])
    assert len(result) == 3
    assert len({len(e.vector) for e in result}) == 1
    assert result[0].vector == result[2].vector
    assert result[0].vector != result[1].vector
    assert await provider.embed([]) == ()
    with pytest.raises(ValidationFailedError):
        await provider.embed(["ok", "  "])


@pytest.mark.contract
@pytest.mark.parametrize("factory", GATEWAYS)
async def test_completion_limits(factory: Callable[[], LlmGateway]) -> None:
    gateway = factory()
    assert isinstance(gateway, LlmGateway)
    short = await gateway.complete(CompletionRequest(prompt="a b c", max_tokens=10))
    assert short.finish_reason is FinishReason.STOP
    assert short.output_tokens == 3
    cut = await gateway.complete(CompletionRequest(prompt="a b c d e", max_tokens=2))
    assert cut.finish_reason is FinishReason.LENGTH
    assert cut.output_tokens == 2
    assert cut.text == "a b"
    exact = await gateway.complete(CompletionRequest(prompt="a b", max_tokens=2))
    assert exact.finish_reason is FinishReason.STOP


def test_request_and_fake_validation() -> None:
    with pytest.raises(ValidationError):
        CompletionRequest(prompt="", max_tokens=5)
    with pytest.raises(ValidationError):
        CompletionRequest(prompt="x", temperature=3.0)
    with pytest.raises(ValueError, match="dimensions"):
        HashEmbeddingProvider(0)
