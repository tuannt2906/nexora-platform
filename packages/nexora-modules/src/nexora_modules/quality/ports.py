"""Public interfaces of the quality module."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from nexora_modules.quality.models import QualityReport, QualityRule


@runtime_checkable
class QualityEvaluator(Protocol):
    async def evaluate(
        self, rows: Sequence[Mapping[str, Any]], rules: Sequence[QualityRule]
    ) -> QualityReport:
        """Evaluate every rule over every row.

        Raises ValidationFailedError when rule ids are not unique. One result per rule, in
        the order given. A missing column is treated as NULL.
        """
        ...
