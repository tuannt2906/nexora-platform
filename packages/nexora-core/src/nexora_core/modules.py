"""Domain-module descriptor (`module.toml`) model and loader.

Every domain module ships a ``module.toml`` declaring its responsibilities, public
interfaces, dependencies, configuration and acceptance criteria. ``make validate`` checks
the descriptor against the code (interfaces must import, evidence files must exist), so the
status shown to users is derived from facts and cannot silently rot.
"""

from __future__ import annotations

import enum
import tomllib
from importlib import resources
from importlib.resources.abc import Traversable

from pydantic import BaseModel, ConfigDict, Field

from nexora_core.engines import EngineKind, Maturity
from nexora_core.errors import ConfigurationError


class CriterionStatus(enum.StrEnum):
    MET = "met"  # a test exists, passes in CI, and `evidence` points at it
    UNMET = "unmet"  # in scope for the current maturity but not satisfied yet
    PLANNED = "planned"  # belongs to a later maturity level


class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[A-Z]{2,5}-\d{1,3}$")
    criterion: str
    status: CriterionStatus
    evidence: str | None = Field(
        default=None, description="Repo-relative path of the test proving a MET criterion"
    )


class ConfigKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(pattern=r"^NEXORA_[A-Z0-9_]+$")
    description: str
    secret: bool = False


class ModuleSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    title: str
    maturity: Maturity
    summary: str
    responsibilities: tuple[str, ...] = Field(min_length=1)
    public_interfaces: tuple[str, ...] = Field(min_length=1)
    depends_on: tuple[str, ...] = ()
    engines: tuple[EngineKind, ...] = ()
    config: tuple[ConfigKey, ...] = ()
    acceptance: tuple[AcceptanceCriterion, ...] = Field(min_length=1)


def parse_module_spec(text: str) -> ModuleSpec:
    try:
        return ModuleSpec.model_validate(tomllib.loads(text))
    except (tomllib.TOMLDecodeError, ValueError) as exc:
        raise ConfigurationError(f"invalid module.toml: {exc}") from exc


def load_module_specs(package: str, ids: tuple[str, ...]) -> list[ModuleSpec]:
    """Load ``<package>.<id>/module.toml`` for each module id (declared order)."""
    specs: list[ModuleSpec] = []
    for module_id in ids:
        sub: Traversable = resources.files(f"{package}.{module_id}")
        text = (sub / "module.toml").read_text(encoding="utf-8")
        spec = parse_module_spec(text)
        if spec.id != module_id:
            raise ConfigurationError(f"{package}.{module_id}/module.toml declares id '{spec.id}'")
        specs.append(spec)
    return specs
