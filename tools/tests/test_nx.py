"""Tests for the task runner policy: missing tools, CI strictness, scoping, exit codes."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("nx_under_test", ROOT / "tools" / "nx.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


nx = _load()


def test_missing_tool_is_loud_skip_locally_and_failure_in_ci(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nx, "IS_CI", False)
    ctx = nx.Context()
    assert nx.missing(ctx, "helm", "install it").status == nx.SKIP

    monkeypatch.setattr(nx, "IS_CI", True)
    assert nx.missing(ctx, "helm", "install it").status == nx.FAIL
    assert [r.status for r in ctx.results] == [nx.SKIP, nx.FAIL]


def test_integration_tests_never_pass_silently(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEXORA_TEST_DATABASE_URL", raising=False)
    for is_ci, expected in ((False, nx.SKIP), (True, nx.FAIL)):
        monkeypatch.setattr(nx, "IS_CI", is_ci)
        ctx = nx.Context()
        nx.task_test_integration(ctx)
        assert [r.status for r in ctx.results] == [expected]
        assert "NOT executed" in ctx.results[0].detail


def test_scope_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    for only, py, web in (("all", True, True), ("python", True, False), ("web", False, True)):
        monkeypatch.setattr(nx, "ONLY", only)
        assert (nx.want_py(), nx.want_web()) == (py, web)


def test_out_of_scope_steps_are_not_executed_or_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nx, "ONLY", "web")
    ctx = nx.Context()
    result = nx.py_step(ctx, "ruff", ["ruff", "--version"])
    assert result.detail == "out of scope"
    assert ctx.results == []  # nothing recorded: it must not count as a pass


def test_step_propagates_exit_codes() -> None:
    ctx = nx.Context()
    ok = nx.step(ctx, "ok", [sys.executable, "-c", "raise SystemExit(0)"])
    bad = nx.step(ctx, "bad", [sys.executable, "-c", "raise SystemExit(3)"])
    assert (ok.status, bad.status) == (nx.PASS, nx.FAIL)
    assert bad.detail == "exit code 3"


def test_summary_exit_code_depends_only_on_failures(capsys: pytest.CaptureFixture[str]) -> None:
    passed = nx.Result("a", nx.PASS)
    skipped = nx.Result("b", nx.SKIP, "tool not available")
    failed = nx.Result("c", nx.FAIL)
    assert nx.summarize([passed, skipped]) == 0
    assert nx.summarize([passed, skipped, failed]) == 1
    assert "SKIPPED (NOT verified here): b" in capsys.readouterr().out


def test_every_required_gate_is_a_runner_task_and_makefile_target() -> None:
    required = {
        "lint",
        "typecheck",
        "test",
        "test-unit",
        "test-contract",
        "validate",
        "build",
        "security-check",
    }
    assert required <= set(nx.TASKS)
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in required:
        assert f"\n{target}:" in makefile, f"Makefile lacks target {target}"
        assert f"@$(NX) {target}" in makefile
