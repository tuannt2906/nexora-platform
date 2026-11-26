"""Data types crossing the lakehouse port boundary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TableIdentifier(BaseModel):
    model_config = ConfigDict(frozen=True)

    namespace: str = Field(min_length=1, description="Dotted namespace, e.g. sales.raw")
    name: str = Field(min_length=1)

    def __str__(self) -> str:
        return f"{self.namespace}.{self.name}"


class ColumnDef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    nullable: bool = True


class TableMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: TableIdentifier
    columns: tuple[ColumnDef, ...]
    location: str = Field(min_length=1, description="URI of the table root in object storage")
    current_snapshot_id: int | None = None


class ObjectInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1)
    size: int = Field(ge=0)
