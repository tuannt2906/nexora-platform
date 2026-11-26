from __future__ import annotations

from collections.abc import Callable

import pytest

from nexora_core.errors import ValidationFailedError
from nexora_modules.observability import MetricSample, MetricsQuery
from nexora_modules.observability.fakes import InMemoryMetricsQuery


def make_query() -> MetricsQuery:
    return InMemoryMetricsQuery(
        {
            "http_requests_total": [
                MetricSample(labels={"service": "api", "code": "200"}, value=10, timestamp=1.0),
                MetricSample(labels={"service": "api", "code": "500"}, value=1, timestamp=1.0),
                MetricSample(labels={"service": "web", "code": "200"}, value=7, timestamp=1.0),
            ]
        }
    )


QUERIES = [pytest.param(make_query, id="in-memory")]


@pytest.mark.contract
@pytest.mark.parametrize("factory", QUERIES)
async def test_selectors(factory: Callable[[], MetricsQuery]) -> None:
    mq = factory()
    assert isinstance(mq, MetricsQuery)
    assert len((await mq.instant_query("http_requests_total")).samples) == 3
    api = await mq.instant_query('http_requests_total{service="api", code="500"}')
    assert [s.value for s in api.samples] == [1]
    assert (await mq.instant_query('http_requests_total{service="none"}')).samples == ()
    assert (await mq.instant_query("unknown_metric")).samples == ()


@pytest.mark.contract
@pytest.mark.parametrize("factory", QUERIES)
@pytest.mark.parametrize("bad", ["", "   ", "rate(x[5m])", 'm{a=~"x"}', "1 +"])
async def test_invalid_expressions(factory: Callable[[], MetricsQuery], bad: str) -> None:
    with pytest.raises(ValidationFailedError):
        await factory().instant_query(bad)
