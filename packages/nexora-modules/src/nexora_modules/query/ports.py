"""Public interfaces of the query module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexora_modules.query.models import QueryRequest, QueryResult


@runtime_checkable
class QueryEngine(Protocol):
    async def execute(self, request: QueryRequest) -> QueryResult:
        """Run a READ-ONLY statement.

        Raises ValidationFailedError for non-read-only or unparsable SQL, NotFoundError for
        unknown relations. ``truncated`` is True when more than ``max_rows`` rows matched.
        """
        ...

    async def explain(self, sql: str) -> str:
        """Human-readable plan for a read-only statement (same errors as ``execute``)."""
        ...
