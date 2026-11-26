from __future__ import annotations

from collections.abc import Callable

import pytest

from nexora_core.errors import NotFoundError, ValidationFailedError
from nexora_modules.query import QueryEngine, QueryRequest
from nexora_modules.query.fakes import InMemoryQueryEngine


def make_engine() -> QueryEngine:
    return InMemoryQueryEngine(
        {"sales.orders": [{"id": i, "total": i * 10} for i in range(5)], "sales.empty": []}
    )


ENGINES = [pytest.param(make_engine, id="in-memory")]


@pytest.mark.contract
@pytest.mark.parametrize("factory", ENGINES)
async def test_execute_and_truncation(factory: Callable[[], QueryEngine]) -> None:
    engine = factory()
    assert isinstance(engine, QueryEngine)
    full = await engine.execute(QueryRequest(sql="SELECT id, total FROM sales.orders"))
    assert full.columns == ("id", "total")
    assert len(full.rows) == 5
    assert not full.truncated
    cut = await engine.execute(QueryRequest(sql="select * from sales.orders;", max_rows=2))
    assert len(cut.rows) == 2
    assert cut.truncated
    assert cut.rows[1] == (1, 10)


@pytest.mark.contract
@pytest.mark.parametrize("factory", ENGINES)
async def test_empty_table_and_explain(factory: Callable[[], QueryEngine]) -> None:
    engine = factory()
    empty = await engine.execute(QueryRequest(sql="SELECT * FROM sales.empty"))
    assert empty.rows == ()
    assert "sales.orders" in await engine.explain("SELECT id FROM sales.orders")


@pytest.mark.contract
@pytest.mark.parametrize("factory", ENGINES)
async def test_read_only_and_unknown_relation(factory: Callable[[], QueryEngine]) -> None:
    engine = factory()
    with pytest.raises(ValidationFailedError):
        await engine.execute(QueryRequest(sql="DROP TABLE sales.orders"))
    with pytest.raises(ValidationFailedError):
        await engine.explain("DELETE FROM sales.orders")
    with pytest.raises(NotFoundError):
        await engine.execute(QueryRequest(sql="SELECT * FROM nope.nothing"))
