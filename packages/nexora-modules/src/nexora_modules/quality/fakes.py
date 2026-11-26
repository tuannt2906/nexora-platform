"""The quality evaluator is itself a real, engine-independent implementation.

This alias exists so every module exposes ``fakes.py`` and contract suites can treat all
modules uniformly. A future engine-pushdown evaluator (Trino/Spark) joins the same suite.
"""

from __future__ import annotations

from nexora_modules.quality.evaluator import RuleQualityEvaluator

InMemoryQualityEvaluator = RuleQualityEvaluator

__all__ = ["InMemoryQualityEvaluator"]
