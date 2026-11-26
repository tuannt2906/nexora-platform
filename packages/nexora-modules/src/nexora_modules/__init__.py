"""NEXORA domain modules.

Layout of every module package ``nexora_modules.<id>``:

* ``module.toml``  -- responsibilities, public interfaces, dependencies, config, acceptance
* ``ports.py``     -- the public interfaces (typing.Protocol) other code may depend on
* ``models.py``    -- immutable data types crossing the port boundary
* ``fakes.py``     -- in-memory reference implementation used by contract tests

Modules must not import each other nor ``nexora_modules.adapters`` (enforced by import-linter).
"""

from __future__ import annotations

from nexora_core.modules import ModuleSpec, load_module_specs

MODULE_IDS: tuple[str, ...] = (
    "ingestion",
    "cdc",
    "streaming",
    "processing",
    "lakehouse",
    "query",
    "orchestration",
    "governance",
    "quality",
    "lineage",
    "observability",
    "ai",
)


def load_modules() -> list[ModuleSpec]:
    """Load and validate every module descriptor."""
    return load_module_specs(__name__, MODULE_IDS)
