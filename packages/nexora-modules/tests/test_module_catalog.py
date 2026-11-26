"""Validates the module descriptors against the code (facts, not claims)."""

from __future__ import annotations

import importlib
from collections import Counter
from pathlib import Path

import pytest

import nexora_modules
from nexora_core.modules import CriterionStatus, ModuleSpec
from nexora_modules import MODULE_IDS, load_modules


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        pyproject = parent / "pyproject.toml"
        if pyproject.is_file() and "[tool.importlinter]" in pyproject.read_text(encoding="utf-8"):
            return parent
    raise AssertionError("repository root not found")


@pytest.fixture(scope="module")
def specs() -> list[ModuleSpec]:
    return load_modules()


@pytest.mark.contract
def test_twelve_modules_in_declared_order(specs: list[ModuleSpec]) -> None:
    assert len(specs) == 12
    assert tuple(s.id for s in specs) == MODULE_IDS
    assert nexora_modules.MODULE_IDS == MODULE_IDS


@pytest.mark.contract
def test_public_interfaces_import(specs: list[ModuleSpec]) -> None:
    for spec in specs:
        for dotted in spec.public_interfaces:
            module_path, _, attr = dotted.rpartition(".")
            assert module_path.startswith(f"nexora_modules.{spec.id}."), dotted
            obj = getattr(importlib.import_module(module_path), attr, None)
            assert obj is not None, f"{dotted} does not exist"


@pytest.mark.contract
def test_met_criteria_have_existing_evidence(specs: list[ModuleSpec]) -> None:
    root = repo_root()
    for spec in specs:
        for criterion in spec.acceptance:
            if criterion.status is CriterionStatus.MET:
                assert criterion.evidence, f"{criterion.id}: met criterion without evidence"
                assert (root / criterion.evidence).is_file(), (
                    f"{criterion.id}: evidence {criterion.evidence} missing"
                )
            else:
                assert criterion.evidence is None, (
                    f"{criterion.id}: only met criteria carry evidence"
                )


@pytest.mark.contract
def test_every_module_has_met_and_planned_criteria(specs: list[ModuleSpec]) -> None:
    for spec in specs:
        statuses = {c.status for c in spec.acceptance}
        assert CriterionStatus.MET in statuses, spec.id
        assert CriterionStatus.PLANNED in statuses, spec.id


@pytest.mark.contract
def test_criterion_ids_unique_and_prefixed(specs: list[ModuleSpec]) -> None:
    counts = Counter(c.id for s in specs for c in s.acceptance)
    assert [i for i, n in counts.items() if n > 1] == []
    for spec in specs:
        prefixes = {c.id.split("-")[0] for c in spec.acceptance}
        assert len(prefixes) == 1, f"{spec.id}: mixed criterion prefixes {prefixes}"


@pytest.mark.contract
def test_depends_on_references_existing_modules_and_is_acyclic(specs: list[ModuleSpec]) -> None:
    ids = {s.id for s in specs}
    graph = {s.id: set(s.depends_on) for s in specs}
    for module_id, deps in graph.items():
        assert deps <= ids, f"{module_id} depends on unknown module"
        assert module_id not in deps

    resolved: set[str] = set()
    remaining = dict(graph)
    while remaining:
        ready = [m for m, deps in remaining.items() if deps <= resolved]
        assert ready, f"dependency cycle among {sorted(remaining)}"
        for module_id in ready:
            resolved.add(module_id)
            del remaining[module_id]


@pytest.mark.contract
def test_engines_and_maturity_are_honest(specs: list[ModuleSpec]) -> None:
    for spec in specs:
        # Nothing may claim to be verified against a real engine before it has been.
        assert spec.maturity.value in {"contract", "functional"}, spec.id
        if spec.maturity.value == "functional":
            assert not spec.engines, f"{spec.id}: functional-without-engine is only for pure logic"


@pytest.mark.contract
def test_config_keys_are_unique(specs: list[ModuleSpec]) -> None:
    keys = Counter(c.key for s in specs for c in s.config)
    assert [k for k, n in keys.items() if n > 1] == []
