"""Federated query: read-only SQL execution (Trino)."""

from nexora_modules.query.models import QueryRequest, QueryResult
from nexora_modules.query.ports import QueryEngine

__all__ = ["QueryEngine", "QueryRequest", "QueryResult"]
