"""Data types crossing the quality port boundary."""

from __future__ import annotations

import enum
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_PATTERN_LENGTH = 500


class RuleKind(enum.StrEnum):
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    RANGE = "range"
    REGEX = "regex"
    ACCEPTED_VALUES = "accepted_values"


class QualityRule(BaseModel):
    """One declarative check on one column. Parameters required depend on ``kind``."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1, max_length=128)
    kind: RuleKind
    column: str = Field(min_length=1)
    min: float | None = None
    max: float | None = None
    pattern: str | None = Field(default=None, max_length=MAX_PATTERN_LENGTH)
    values: tuple[str | int | float, ...] | None = None

    @model_validator(mode="after")
    def _check_parameters(self) -> QualityRule:
        if self.kind is RuleKind.RANGE:
            if self.min is None and self.max is None:
                raise ValueError("range rule needs min and/or max")
            if self.min is not None and self.max is not None and self.min > self.max:
                raise ValueError("range rule has min > max")
        elif self.kind is RuleKind.REGEX:
            if not self.pattern:
                raise ValueError("regex rule needs a pattern")
            try:
                re.compile(self.pattern)
            except re.error as exc:
                raise ValueError(f"invalid regex pattern: {exc}") from exc
        elif self.kind is RuleKind.ACCEPTED_VALUES and not self.values:
            raise ValueError("accepted_values rule needs a non-empty values list")
        return self


class RuleResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    passed: bool
    failed_count: int = Field(ge=0)
    total_count: int = Field(ge=0)


class QualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_count: int = Field(ge=0)
    results: tuple[RuleResult, ...]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)
