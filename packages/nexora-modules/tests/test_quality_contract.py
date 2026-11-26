from __future__ import annotations

from collections.abc import Callable

import pytest
from pydantic import ValidationError

from nexora_core.errors import ValidationFailedError
from nexora_modules.quality import QualityEvaluator, QualityRule, RuleKind
from nexora_modules.quality.fakes import InMemoryQualityEvaluator

EVALUATORS = [pytest.param(InMemoryQualityEvaluator, id="in-process")]

ROWS = [
    {"id": 1, "email": "a@x.io", "age": 30, "tier": "gold"},
    {"id": 2, "email": "bad", "age": 200, "tier": "silver"},
    {"id": 2, "email": None, "age": -1, "tier": "bronze"},
    {"id": None, "email": "c@x.io", "age": "n/a", "tier": "gold"},
]


async def failed(evaluator: QualityEvaluator, rule: QualityRule) -> int:
    report = await evaluator.evaluate(ROWS, [rule])
    assert report.row_count == len(ROWS)
    (result,) = report.results
    assert result.total_count == len(ROWS)
    assert result.passed == (result.failed_count == 0)
    return result.failed_count


@pytest.mark.contract
@pytest.mark.parametrize("factory", EVALUATORS)
async def test_rule_semantics(factory: Callable[[], QualityEvaluator]) -> None:
    ev = factory()
    assert isinstance(ev, QualityEvaluator)
    r = QualityRule
    assert await failed(ev, r(id="a", kind=RuleKind.NOT_NULL, column="id")) == 1
    assert await failed(ev, r(id="b", kind=RuleKind.NOT_NULL, column="missing_col")) == 4
    assert await failed(ev, r(id="c", kind=RuleKind.UNIQUE, column="id")) == 2  # both id=2 rows
    assert await failed(ev, r(id="d", kind=RuleKind.RANGE, column="age", min=0, max=120)) == 3
    assert await failed(ev, r(id="e", kind=RuleKind.RANGE, column="age", max=100)) == 2
    assert (
        await failed(ev, r(id="f", kind=RuleKind.REGEX, column="email", pattern=r"[^@]+@x\.io"))
        == 1
    )
    assert (
        await failed(
            ev, r(id="g", kind=RuleKind.ACCEPTED_VALUES, column="tier", values=("gold", "silver"))
        )
        == 1
    )


@pytest.mark.contract
@pytest.mark.parametrize("factory", EVALUATORS)
async def test_report_shape_and_edge_cases(factory: Callable[[], QualityEvaluator]) -> None:
    ev = factory()
    rules = [
        QualityRule(id="z", kind=RuleKind.NOT_NULL, column="id"),
        QualityRule(id="y", kind=RuleKind.UNIQUE, column="tier"),
    ]
    report = await ev.evaluate(ROWS, rules)
    assert [x.rule_id for x in report.results] == ["z", "y"]
    assert not report.passed
    empty = await ev.evaluate([], rules)
    assert empty.passed
    assert empty.row_count == 0
    assert (await ev.evaluate(ROWS, [])).passed
    with pytest.raises(ValidationFailedError):
        await ev.evaluate(ROWS, [rules[0], rules[0]])


@pytest.mark.contract
@pytest.mark.parametrize("factory", EVALUATORS)
async def test_unhashable_and_boolean_values(factory: Callable[[], QualityEvaluator]) -> None:
    ev = factory()
    rows = [{"v": [1, 2]}, {"v": [1, 2]}, {"v": True}]
    uniq = await ev.evaluate(rows, [QualityRule(id="u", kind=RuleKind.UNIQUE, column="v")])
    assert uniq.results[0].failed_count == 2
    rng = await ev.evaluate(
        rows, [QualityRule(id="r", kind=RuleKind.RANGE, column="v", min=0, max=5)]
    )
    assert rng.results[0].failed_count == 3  # lists and bool are not numbers


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kind": RuleKind.RANGE},
        {"kind": RuleKind.RANGE, "min": 5, "max": 1},
        {"kind": RuleKind.REGEX},
        {"kind": RuleKind.REGEX, "pattern": "("},
        {"kind": RuleKind.ACCEPTED_VALUES},
        {"kind": RuleKind.ACCEPTED_VALUES, "values": ()},
    ],
)
def test_invalid_rules_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        QualityRule(id="x", column="c", **kwargs)  # type: ignore[arg-type]
