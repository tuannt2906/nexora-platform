"""In-memory reference implementation.

Deliberately tiny: understands only ``SELECT <cols|*> FROM <table>``. It exists to pin down
the port semantics (read-only, truncation, error types), not to emulate SQL.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from nexora_core.errors import NotFoundError, ValidationFailedError
from nexora_modules.query.models import QueryRequest, QueryResult

_SELECT = re.compile(
    r"^\s*select\s+(?P<cols>.+?)\s+from\s+(?P<table>[A-Za-z0-9_.]+)\s*;?\s*$",
    re.IGNORECASE | re.DOTALL,
)


class InMemoryQueryEngine:
    def __init__(self, tables: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
        self._tables = {k: tuple(v) for k, v in tables.items()}

    def _plan(self, sql: str) -> tuple[str, list[str]]:
        match = _SELECT.match(sql)
        if match is None:
            raise ValidationFailedError("only 'SELECT <columns> FROM <table>' is supported")
        table = match["table"]
        rows = self._tables.get(table)
        if rows is None:
            raise NotFoundError(f"unknown relation '{table}'")
        cols_raw = match["cols"].strip()
        if cols_raw == "*":
            columns = list(rows[0]) if rows else []
        else:
            columns = [c.strip() for c in cols_raw.split(",")]
        return table, columns

    async def execute(self, request: QueryRequest) -> QueryResult:
        table, columns = self._plan(request.sql)
        data = self._tables[table]
        selected = data[: request.max_rows]
        return QueryResult(
            columns=tuple(columns),
            rows=tuple(tuple(row.get(c) for c in columns) for row in selected),
            truncated=len(data) > request.max_rows,
        )

    async def explain(self, sql: str) -> str:
        table, columns = self._plan(sql)
        return f"Scan[{table}] -> Project[{', '.join(columns)}]"
