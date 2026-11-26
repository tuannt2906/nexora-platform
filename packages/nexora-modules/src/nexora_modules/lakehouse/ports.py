"""Public interfaces of the lakehouse module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexora_modules.lakehouse.models import ObjectInfo, TableIdentifier, TableMetadata


@runtime_checkable
class TableCatalog(Protocol):
    async def list_namespaces(self) -> tuple[str, ...]:
        """Namespaces, sorted ascending."""
        ...

    async def list_tables(self, namespace: str) -> tuple[str, ...]:
        """Table names in a namespace, sorted. Raises NotFoundError for an unknown namespace."""
        ...

    async def load_table(self, identifier: TableIdentifier) -> TableMetadata:
        """Raises NotFoundError for an unknown table."""
        ...


@runtime_checkable
class ObjectStore(Protocol):
    async def put(self, key: str, data: bytes) -> ObjectInfo:
        """Create or overwrite an object."""
        ...

    async def get(self, key: str) -> bytes:
        """Raises NotFoundError for an unknown key."""
        ...

    async def list(self, prefix: str) -> tuple[ObjectInfo, ...]:
        """Objects whose key starts with ``prefix``, sorted by key."""
        ...
