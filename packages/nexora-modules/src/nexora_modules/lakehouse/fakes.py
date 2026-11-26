"""In-memory reference implementations (deterministic, no I/O)."""

from __future__ import annotations

from nexora_core.errors import ConflictError, NotFoundError
from nexora_modules.lakehouse.models import ObjectInfo, TableIdentifier, TableMetadata


class InMemoryTableCatalog:
    def __init__(self) -> None:
        self._tables: dict[str, dict[str, TableMetadata]] = {}

    def register(self, metadata: TableMetadata) -> None:
        """Test helper: the port is read-only; real catalogs are populated by engines."""
        ident = metadata.identifier
        tables = self._tables.setdefault(ident.namespace, {})
        if ident.name in tables:
            raise ConflictError(f"table '{ident}' already registered")
        tables[ident.name] = metadata

    async def list_namespaces(self) -> tuple[str, ...]:
        return tuple(sorted(self._tables))

    async def list_tables(self, namespace: str) -> tuple[str, ...]:
        try:
            return tuple(sorted(self._tables[namespace]))
        except KeyError:
            raise NotFoundError(f"unknown namespace '{namespace}'") from None

    async def load_table(self, identifier: TableIdentifier) -> TableMetadata:
        try:
            return self._tables[identifier.namespace][identifier.name]
        except KeyError:
            raise NotFoundError(f"unknown table '{identifier}'") from None


class InMemoryObjectStore:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes) -> ObjectInfo:
        self._objects[key] = data
        return ObjectInfo(key=key, size=len(data))

    async def get(self, key: str) -> bytes:
        try:
            return self._objects[key]
        except KeyError:
            raise NotFoundError(f"unknown object '{key}'") from None

    async def list(self, prefix: str) -> tuple[ObjectInfo, ...]:
        return tuple(
            ObjectInfo(key=k, size=len(v))
            for k, v in sorted(self._objects.items())
            if k.startswith(prefix)
        )
