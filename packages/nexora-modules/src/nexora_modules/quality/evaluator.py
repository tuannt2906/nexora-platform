"""Rule evaluation logic (pure Python, engine independent).

Semantics (SQL-like, documented because they are the contract):

* ``not_null``: a row fails when the value is NULL / missing.
* ``unique``: NULLs are ignored; every row whose value occurs more than once fails.
* ``range``: NULLs are ignored; bounds are inclusive; non-numeric values (and booleans) fail.
* ``regex``: NULLs are ignored; the value must be a string matching the pattern completely.
* ``accepted_values``: NULLs are ignored; any other value not in the list fails.

Pair NULL-ignoring rules with ``not_null`` to also forbid NULLs.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from nexora_core.errors import ValidationFailedError
from nexora_modules.quality.models import QualityReport, QualityRule, RuleKind, RuleResult


def _hashable(value: Any) -> Any:
    try:
        hash(value)
    except TypeError:
        return repr(value)
    return value


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _failures(rows: Sequence[Mapping[str, Any]], rule: QualityRule) -> int:
    values = [row.get(rule.column) for row in rows]
    non_null = [v for v in values if v is not None]
    predicate: Callable[[Any], bool]
    match rule.kind:
        case RuleKind.NOT_NULL:
            return len(values) - len(non_null)
        case RuleKind.UNIQUE:
            counts = Counter(_hashable(v) for v in non_null)
            return sum(1 for v in non_null if counts[_hashable(v)] > 1)
        case RuleKind.RANGE:
            lo, hi = rule.min, rule.max

            def predicate(v: Any) -> bool:
                return _is_number(v) and (lo is None or v >= lo) and (hi is None or v <= hi)

        case RuleKind.REGEX:
            compiled = re.compile(rule.pattern or "")

            def predicate(v: Any) -> bool:
                return isinstance(v, str) and compiled.fullmatch(v) is not None

        case RuleKind.ACCEPTED_VALUES:
            allowed = set(rule.values or ())

            def predicate(v: Any) -> bool:
                return _hashable(v) in allowed

    return sum(1 for v in non_null if not predicate(v))


class RuleQualityEvaluator:
    async def evaluate(
        self, rows: Sequence[Mapping[str, Any]], rules: Sequence[QualityRule]
    ) -> QualityReport:
        ids = [r.id for r in rules]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValidationFailedError(f"duplicate rule ids: {', '.join(duplicates)}")
        results = []
        for rule in rules:
            failed = _failures(rows, rule)
            results.append(
                RuleResult(
                    rule_id=rule.id,
                    passed=failed == 0,
                    failed_count=failed,
                    total_count=len(rows),
                )
            )
        return QualityReport(row_count=len(rows), results=tuple(results))
