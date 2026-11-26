"""Composition root: the only place that wires settings, persistence and adapters."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine

from nexora_control_plane.db import Repository, create_db_engine
from nexora_control_plane.settings import Settings
from nexora_core.engines import AdapterRegistry
from nexora_core.modules import ModuleSpec
from nexora_modules import load_modules
from nexora_modules.adapters import default_registry


@dataclass
class Container:
    settings: Settings
    db_engine: Engine
    repository: Repository
    registry: AdapterRegistry
    modules: list[ModuleSpec]

    @classmethod
    def build(cls, settings: Settings, *, registry: AdapterRegistry | None = None) -> Container:
        engine = create_db_engine(settings.database_url.get_secret_value())
        return cls(
            settings=settings,
            db_engine=engine,
            repository=Repository(engine),
            registry=registry or default_registry(),
            modules=load_modules(),
        )

    def dispose(self) -> None:
        self.db_engine.dispose()
