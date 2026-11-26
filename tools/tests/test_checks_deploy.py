"""Tests for tools/checks/deploy.py: the real repo passes, and each policy actually bites."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "nexora_check_deploy", REPO / "tools" / "checks" / "deploy.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


deploy = _load()


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A private copy of the deployment assets that tests may mutate."""
    for sub in ("deploy", "infra/docker"):
        shutil.copytree(REPO / sub, tmp_path / sub)
    return tmp_path


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not found in {path}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _assert_problem(problems: list[str], needle: str) -> None:
    assert any(needle in p for p in problems), f"no problem containing {needle!r} in {problems}"


# --------------------------------------------------------------------------- real repo


def test_repository_assets_pass_static_checks() -> None:
    assert deploy.run(REPO) == []


def test_module_interface() -> None:
    assert deploy.NAME == "deploy"
    assert callable(deploy.run)
    assert callable(deploy.optional_steps)


# --------------------------------------------------------------------------- images


@pytest.mark.parametrize(
    "ref",
    [
        "postgres:16.16-bookworm",
        "ghcr.io/o/p/control-plane:0123abcdef01",
        "python:3.11.18-slim-bookworm@sha256:" + "a" * 64,
        "ghcr.io/o/p/web@sha256:" + "b" * 64,
        "${NEXORA_IMAGE_REGISTRY:?x}/web:${NEXORA_IMAGE_TAG:?set it}",
    ],
)
def test_image_policy_accepts_pinned(ref: str) -> None:
    assert deploy.image_problem(ref) is None


@pytest.mark.parametrize(
    "ref",
    [
        "nginx",
        "nginx:latest",
        "python:3",
        "python:3.11-slim",
        "python:slim",
        "x/y:${OTHER_TAG}",
        "x/y:{{ .Values.t }}",
    ],
)
def test_image_policy_rejects_floating(ref: str) -> None:
    assert deploy.image_problem(ref) is not None


def test_compose_latest_tag_is_rejected(tree: Path) -> None:
    _edit(tree / "deploy/compose/docker-compose.yml", "postgres:16.16-bookworm", "postgres:latest")
    _assert_problem(deploy.run(tree), "floating tag")


def test_dockerfile_floating_base_is_rejected(tree: Path) -> None:
    _edit(
        tree / "infra/docker/control-plane.Dockerfile",
        "FROM python:3.11.18-slim-bookworm AS runtime",
        "FROM python:3.11-slim AS runtime",
    )
    _assert_problem(deploy.run(tree), "control-plane.Dockerfile")


def test_dockerfile_stage_reference_is_allowed(tree: Path) -> None:
    dockerfile = tree / "infra/docker/control-plane.Dockerfile"
    dockerfile.write_text(
        dockerfile.read_text(encoding="utf-8") + "\nFROM runtime AS final\n", encoding="utf-8"
    )
    assert deploy.run(tree) == []


# --------------------------------------------------------------------------- secrets


def test_literal_secret_in_compose_is_rejected(tree: Path) -> None:
    _edit(
        tree / "deploy/compose/docker-compose.yml",
        "POSTGRES_PASSWORD: ${NEXORA_POSTGRES_PASSWORD:?set NEXORA_POSTGRES_PASSWORD in .env}",
        "POSTGRES_PASSWORD: hunter2hunter2",
    )
    _assert_problem(deploy.run(tree), "literal secret")


def test_literal_credentials_in_url_are_rejected(tree: Path) -> None:
    _edit(
        tree / "deploy/compose/docker-compose.yml",
        "nexora:${NEXORA_POSTGRES_PASSWORD:?set NEXORA_POSTGRES_PASSWORD in .env}@postgres",
        "nexora:hunter2@postgres",
    )
    _assert_problem(deploy.run(tree), "credentials in a URL")


def test_env_example_with_real_value_is_rejected(tree: Path) -> None:
    _edit(
        tree / "deploy/compose/.env.example", "NEXORA_API_TOKEN=CHANGE_ME", "NEXORA_API_TOKEN=abc"
    )
    _assert_problem(deploy.run(tree), "must be empty or start with CHANGE_ME")


def test_committed_kubernetes_secret_is_rejected(tree: Path) -> None:
    (tree / "deploy/kubernetes/base/secret.yaml").write_text(
        "apiVersion: v1\nkind: Secret\nmetadata:\n  name: x\nstringData:\n  a: b\n",
        encoding="utf-8",
    )
    _assert_problem(deploy.run(tree), "kind Secret must not be committed")


def test_private_key_block_is_rejected(tree: Path) -> None:
    (tree / "deploy/compose/leak.txt").write_text(
        "-----BEGIN RSA PRIVATE KEY-----\n", encoding="utf-8"
    )
    _assert_problem(deploy.run(tree), "private key")


# --------------------------------------------------------------------------- kubernetes


@pytest.mark.parametrize(
    ("old", "needle"),
    [
        ("readOnlyRootFilesystem: true", "readOnlyRootFilesystem must be true"),
        ("drop: [ALL]", "capabilities.drop must include ALL"),
        ("allowPrivilegeEscalation: false", "allowPrivilegeEscalation must be false"),
        ("runAsNonRoot: true", "runAsNonRoot must be true"),
        ("type: RuntimeDefault", "seccompProfile must be RuntimeDefault"),
        ("automountServiceAccountToken: false", "automountServiceAccountToken must be false"),
    ],
)
def test_k8s_hardening_regressions_are_rejected(tree: Path, old: str, needle: str) -> None:
    path = tree / "deploy/kubernetes/base/control-plane-deployment.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(old, "unrelated: true"), encoding="utf-8")
    _assert_problem(deploy.run(tree), needle)


def test_k8s_missing_resources_and_probes_are_rejected(tree: Path) -> None:
    path = tree / "deploy/kubernetes/base/web-deployment.yaml"
    text = path.read_text(encoding="utf-8")
    text = text.replace("resources:", "x-resources:").replace("readinessProbe:", "x-probe:")
    path.write_text(text, encoding="utf-8")
    problems = deploy.run(tree)
    _assert_problem(problems, "resources.requests.cpu is required")
    _assert_problem(problems, "readinessProbe is required")


def test_k8s_floating_image_is_rejected(tree: Path) -> None:
    _edit(
        tree / "deploy/kubernetes/base/web-deployment.yaml",
        "nexora-web:0.0.0-overridden-by-overlay",
        "nexora-web:latest",
    )
    _assert_problem(deploy.run(tree), "floating tag")


# --------------------------------------------------------------------------- placeholders


def test_placeholder_outside_overlays_is_rejected(tree: Path) -> None:
    _edit(
        tree / "deploy/kubernetes/base/configmap.yaml",
        "NEXORA_LOG_LEVEL: INFO",
        "NEXORA_LOG_LEVEL: REPLACE_WITH_RELEASE_SHA",
    )
    _assert_problem(deploy.run(tree), "placeholder REPLACE_WITH_RELEASE_SHA not allowed here")


def test_overlay_must_keep_placeholders(tree: Path) -> None:
    _edit(
        tree / "deploy/kubernetes/overlays/production/kustomization.yaml",
        "newTag: REPLACE_WITH_RELEASE_SHA",
        "newTag: abc123.4",
    )
    _assert_problem(deploy.run(tree), "placeholder REPLACE_WITH_RELEASE_SHA is missing")


def test_release_guard_detects_and_accepts_substitution(tree: Path) -> None:
    overlay = tree / "deploy/kubernetes/overlays/production"
    before = deploy.release_placeholder_problems(tree, overlay)
    assert len(before) == 2
    assert all("unsubstituted placeholder" in problem for problem in before)
    kustomization = overlay / "kustomization.yaml"
    text = kustomization.read_text(encoding="utf-8")
    text = text.replace("REPLACE_WITH_RELEASE_SHA", "0123456789abcdef").replace(
        "REPLACE_WITH_OWNER", "acme"
    )
    # keep the explanatory comment from re-triggering the guard
    kustomization.write_text(
        "\n".join(line for line in text.splitlines() if not line.startswith("#")) + "\n",
        encoding="utf-8",
    )
    assert deploy.release_placeholder_problems(tree, overlay) == []


def test_release_guard_cli_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert deploy.main(["--require-substituted"]) == 2
    assert "usage" in capsys.readouterr().err


# --------------------------------------------------------------------------- compose


def test_compose_publishing_extra_ports_is_rejected(tree: Path) -> None:
    _edit(
        tree / "deploy/compose/docker-compose.yml",
        "    restart: unless-stopped\n    environment:\n      POSTGRES_DB",
        "    restart: unless-stopped\n    ports: ['5432:5432']\n"
        "    environment:\n      POSTGRES_DB",
    )
    _assert_problem(deploy.run(tree), "service 'postgres' publishes host ports")


# --------------------------------------------------------------------------- helm values


def test_helm_values_must_not_default_image_tag(tree: Path) -> None:
    _edit(tree / "deploy/helm/nexora/values.yaml", '  tag: ""', "  tag: v1.0.0")
    _assert_problem(deploy.run(tree), "must default to empty")


def test_helm_helpers_must_reject_latest(tree: Path) -> None:
    (tree / "deploy/helm/nexora/templates/_helpers.tpl").write_text("{{/* nothing */}}\n")
    _assert_problem(deploy.run(tree), "_helpers.tpl must")


# --------------------------------------------------------------------------- tool-backed steps


def test_missing_tools_skip_locally(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("CI", raising=False)
    steps = deploy.optional_steps(REPO)
    assert [s[1] for s in steps] == ["skip", "skip", "skip"]
    assert all("not found on PATH" in s[2][0] for s in steps)


@pytest.mark.parametrize("ci_value", ["true", "1"])
def test_missing_tools_fail_in_ci(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ci_value: str
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("CI", ci_value)
    steps = deploy.optional_steps(REPO)
    assert [s[1] for s in steps] == ["fail", "fail", "fail"]


def test_exec_reports_pass_fail_and_expected_failure() -> None:
    python = sys.executable
    ok = deploy._exec("ok", [python, "-c", "pass"], cwd=REPO)
    assert ok[1] == "pass"
    bad = deploy._exec("bad", [python, "-c", "import sys; sys.exit(3)"], cwd=REPO)
    assert bad[1] == "fail"
    expected = deploy._exec(
        "neg",
        [python, "-c", "import sys; sys.stderr.write('image.tag is required'); sys.exit(1)"],
        cwd=REPO,
        expect_failure_containing="image.tag",
    )
    assert expected[1] == "pass"
    unexpected_success = deploy._exec(
        "neg2", [python, "-c", "pass"], cwd=REPO, expect_failure_containing="image.tag"
    )
    assert unexpected_success[1] == "fail"
    wrong_message = deploy._exec(
        "neg3",
        [python, "-c", "import sys; sys.exit(1)"],
        cwd=REPO,
        expect_failure_containing="image.tag",
    )
    assert wrong_message[1] == "fail"
    missing = deploy._exec("missing", ["definitely-not-a-binary-xyz"], cwd=REPO)
    assert missing[1] == "fail"


def test_optional_steps_use_available_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """With all tools 'present' the steps are executed through _exec (stubbed here)."""
    calls: list[str] = []

    def fake_which(name: str) -> str:
        return f"/fake/{name}"

    def fake_exec(label: str, argv: list[str], **_: object) -> tuple[str, str, list[str]]:
        calls.append(label)
        return (label, "pass", [])

    monkeypatch.setattr(deploy.shutil, "which", fake_which)
    monkeypatch.setattr(deploy, "_exec", fake_exec)
    monkeypatch.setattr(deploy, "_rendered_workload_step", lambda label, *_a: (label, "pass", []))
    steps = deploy.optional_steps(REPO)
    assert all(s[1] == "pass" for s in steps)
    assert any(c.startswith("helm lint") for c in calls)
    assert any("kustomize overlays/production" in c for c in calls)
    assert any(c.startswith("docker compose config") for c in calls)
