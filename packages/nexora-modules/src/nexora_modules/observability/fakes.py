"""In-memory reference implementation.

Understands only ``metric_name`` and ``metric_name{label="value", ...}`` (equality matchers).
It pins down the port semantics; it is not a PromQL engine.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from nexora_core.errors import ValidationFailedError
from nexora_modules.observability.models import InstantQueryResult, MetricSample

_SELECTOR = re.compile(r"^\s*(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)\s*(?:\{(?P<matchers>[^}]*)\})?\s*$")
_MATCHER = re.compile(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*"([^"]*)"\s*$')


class InMemoryMetricsQuery:
    def __init__(self, series: Mapping[str, Sequence[MetricSample]]) -> None:
        self._series = {k: tuple(v) for k, v in series.items()}

    async def instant_query(self, promql: str) -> InstantQueryResult:
        match = _SELECTOR.match(promql)
        if match is None:
            raise ValidationFailedError(f"unsupported or invalid PromQL: {promql!r}")
        wanted: dict[str, str] = {}
        if match["matchers"]:
            for part in match["matchers"].split(","):
                m = _MATCHER.match(part)
                if m is None:
                    raise ValidationFailedError(f"unsupported label matcher: {part.strip()!r}")
                wanted[m[1]] = m[2]
        samples = tuple(
            s
            for s in self._series.get(match["name"], ())
            if all(s.labels.get(k) == v for k, v in wanted.items())
        )
        return InstantQueryResult(query=promql, samples=samples)
