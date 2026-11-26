from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    path = ROOT / "tools" / "checks" / "repo_policy.py"
    spec = importlib.util.spec_from_file_location("checks_repo_policy", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


policy = _load()
SHA = "a" * 40


def write(root: Path, rel: str, text: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def workflow(uses: str, permissions: bool = True) -> str:
    perms = "permissions:\n  contents: read\n" if permissions else ""
    return (
        "name: t\non: push\n"
        + perms
        + "jobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n"
        + f"      - uses: {uses}\n"
    )


def test_workflow_actions_must_be_pinned_to_sha(tmp_path: Path) -> None:
    write(tmp_path, ".github/workflows/ci.yml", workflow("actions/checkout@v4"))
    problems = policy.check_workflows(tmp_path)
    assert any("pinned to a commit SHA" in p for p in problems)

    write(tmp_path, ".github/workflows/ci.yml", workflow(f"actions/checkout@{SHA}"))
    assert policy.check_workflows(tmp_path) == []


def test_workflow_requires_permissions_and_forbids_pull_request_target(tmp_path: Path) -> None:
    write(
        tmp_path, ".github/workflows/a.yml", workflow(f"actions/checkout@{SHA}", permissions=False)
    )
    assert any("permissions" in p for p in policy.check_workflows(tmp_path))

    bad = workflow(f"actions/checkout@{SHA}").replace("on: push", "on: pull_request_target")
    write(tmp_path, ".github/workflows/a.yml", bad)
    assert any("pull_request_target" in p for p in policy.check_workflows(tmp_path))


def test_local_actions_are_allowed(tmp_path: Path) -> None:
    write(tmp_path, ".github/workflows/a.yml", workflow("./.github/actions/setup"))
    assert policy.check_workflows(tmp_path) == []


def test_adr_index_must_list_every_adr_with_status(tmp_path: Path) -> None:
    write(tmp_path, "docs/adr/README.md", "# ADRs\n- [0001](0001-first.md)\n")
    write(tmp_path, "docs/adr/0001-first.md", "# 1. First\n\nStatus: Accepted\n")
    write(tmp_path, "docs/adr/0002-second.md", "# 2. Second\n")
    problems = policy.check_adr_index(tmp_path)
    assert "0002-second.md is not listed in docs/adr/README.md" in problems
    assert "0002-second.md: missing `Status:` line" in problems
    assert len(problems) == 2


def test_lockfiles_need_hashes(tmp_path: Path) -> None:
    write(tmp_path, "requirements/prod.txt", "fastapi==1.0\n")
    assert any("no hashes" in p for p in policy.check_lockfiles(tmp_path))
    write(tmp_path, "requirements/prod.txt", "fastapi==1.0 \\\n    --hash=sha256:abc\n")
    assert policy.check_lockfiles(tmp_path) == []


def test_secret_and_workstation_path_detection(tmp_path: Path) -> None:
    write(tmp_path, ".env", "X=1\n")
    write(tmp_path, ".env.example", "X=changeme\n")
    write(tmp_path, "services/a/src/m.py", 'KEY = "AKIAABCDEFGHIJKLMNOP"\n')
    write(
        tmp_path, "services/a/src/n.py", 'P = "C:\\\\Users\\\\bob\\\\x"\nQ = r"C:\\Users\\bob\\x"\n'
    )
    problems = policy.check_no_secrets_or_workstation_paths(tmp_path)
    joined = "\n".join(problems)
    assert ".env: environment file must not be committed" in joined
    assert ".env.example" not in joined
    assert "AWS access key id" in joined
    assert "workstation-specific path" in joined


def test_localhost_forbidden_in_python_sources_but_not_tests(tmp_path: Path) -> None:
    write(tmp_path, "services/a/src/pkg/m.py", 'URL = "http://localhost:8000"\n')
    write(tmp_path, "services/a/tests/test_m.py", 'URL = "http://localhost:8000"\n')
    problems = policy.check_no_localhost_in_python_sources(tmp_path)
    assert problems == ["services/a/src/pkg/m.py: hardcoded localhost/127.0.0.1 address"]


def test_required_files_reported(tmp_path: Path) -> None:
    problems = policy.check_required_files(tmp_path)
    assert "required file missing: README.md" in problems
    assert len(problems) == len(policy.REQUIRED_FILES)


@pytest.mark.parametrize("kind_doc_missing", [True, False])
def test_adapter_contract_docs_cover_every_engine_kind(
    tmp_path: Path, kind_doc_missing: bool
) -> None:
    from nexora_core.engines import EngineKind

    for kind in EngineKind:
        if kind_doc_missing and kind is EngineKind.TRINO:
            continue
        write(tmp_path, f"contracts/adapters/{kind.value}.md", "# doc\n")
    problems = policy.check_adapter_contract_docs(tmp_path)
    assert bool(problems) is kind_doc_missing


def test_crlf_files_are_reported_but_windows_scripts_are_exempt(tmp_path: Path) -> None:
    (tmp_path / "a.yml").write_bytes(b"a: 1\r\nb: 2\r\n")
    (tmp_path / "ok.yml").write_bytes(b"a: 1\nb: 2\n")
    (tmp_path / "run.ps1").write_bytes(b"echo hi\r\n")
    assert policy.check_line_endings(tmp_path) == ["a.yml: CRLF line endings (use LF)"]
