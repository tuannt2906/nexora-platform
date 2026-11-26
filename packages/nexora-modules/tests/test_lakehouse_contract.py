from __future__ import annotations

from collections.abc import Callable

import pytest

from nexora_core.errors import ConflictError, NotFoundError
from nexora_modules.lakehouse import (
    ColumnDef,
    ObjectStore,
    TableCatalog,
    TableIdentifier,
    TableMetadata,
)
from nexora_modules.lakehouse.fakes import InMemoryObjectStore, InMemoryTableCatalog


def table(namespace: str, name: str) -> TableMetadata:
    return TableMetadata(
        identifier=TableIdentifier(namespace=namespace, name=name),
        columns=(ColumnDef(name="id", type="long", nullable=False),),
        location=f"s3://warehouse/{namespace}/{name}",
        current_snapshot_id=1,
    )


def make_catalog() -> TableCatalog:
    catalog = InMemoryTableCatalog()
    catalog.register(table("sales", "orders"))
    catalog.register(table("sales", "items"))
    catalog.register(table("hr", "people"))
    return catalog


CATALOGS = [pytest.param(make_catalog, id="in-memory")]
STORES = [pytest.param(InMemoryObjectStore, id="in-memory")]


@pytest.mark.contract
@pytest.mark.parametrize("factory", CATALOGS)
async def test_catalog_browse(factory: Callable[[], TableCatalog]) -> None:
    catalog = factory()
    assert isinstance(catalog, TableCatalog)
    assert await catalog.list_namespaces() == ("hr", "sales")
    assert await catalog.list_tables("sales") == ("items", "orders")
    meta = await catalog.load_table(TableIdentifier(namespace="sales", name="orders"))
    assert meta.location == "s3://warehouse/sales/orders"
    assert str(meta.identifier) == "sales.orders"


@pytest.mark.contract
@pytest.mark.parametrize("factory", CATALOGS)
async def test_catalog_not_found(factory: Callable[[], TableCatalog]) -> None:
    catalog = factory()
    with pytest.raises(NotFoundError):
        await catalog.list_tables("nope")
    with pytest.raises(NotFoundError):
        await catalog.load_table(TableIdentifier(namespace="sales", name="nope"))


def test_register_duplicate_conflicts() -> None:
    catalog = InMemoryTableCatalog()
    catalog.register(table("a", "t"))
    with pytest.raises(ConflictError):
        catalog.register(table("a", "t"))


@pytest.mark.contract
@pytest.mark.parametrize("factory", STORES)
async def test_object_store_roundtrip(factory: Callable[[], ObjectStore]) -> None:
    store = factory()
    assert isinstance(store, ObjectStore)
    info = await store.put("b/2", b"hello")
    assert info.size == 5
    await store.put("a/1", b"x")
    await store.put("b/1", b"yy")
    assert await store.get("b/2") == b"hello"
    assert [o.key for o in await store.list("b/")] == ["b/1", "b/2"]
    assert [o.key for o in await store.list("")] == ["a/1", "b/1", "b/2"]
    with pytest.raises(NotFoundError):
        await store.get("missing")
