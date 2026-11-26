#!/usr/bin/env python3
"""NEXORA task runner: the single source of truth for every quality gate.

`make <target>` (Linux/CI/servers) and `python tools/nx.py <target>` (Windows workstation,
no `make` required) run exactly the same code, so a green local run means a green CI run.

Rules this runner enforces:
* every gate executes a real tool and propagates its exit code;
* a missing tool is NEVER a silent pass: locally it is a loud SKIP listed in the summary,
  and when CI=true it is a FAILURE;
* nothing here starts Docker, Kubernetes or any data engine unless the target says so.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "apps" / "web"
IS_CI = os.environ.get("CI", "").lower() in {"1", "true", "yes"}
IS_WINDOWS = os.name == "nt"
# NX_ONLY=python|web restricts language-specific gates (CI jobs run per stack); default: all.
ONLY = os.environ.get("NX_ONLY", "all").lower()

PY_SOURCES = [
    "packages/nexora-core/src",
    "packages/nexora-modules/src",
    "services/control-plane/src",
    "sdk/python/src",
]
PY_PACKAGES = [
    "packages/nexora-core",
    "packages/nexora-modules",
    "services/control-plane",
    "sdk/python",
]

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


@dataclass
class Result:
    name: str
    status: str
    detail: str = ""
    seconds: float = 0.0


@dataclass
class Context:
    results: list[Result] = field(default_factory=list)

    def add(self, result: Result) -> Result:
        self.results.append(result)
        marker = {PASS: "[ ok ]", FAIL: "[FAIL]", SKIP: "[SKIP]"}[result.status]
        suffix = f" -- {result.detail}" if result.detail else ""
        print(f"{marker} {result.name}{suffix}", flush=True)
        return result


# --------------------------------------------------------------------------- helpers


def venv_bin() -> Path:
    return ROOT / ".venv" / ("Scripts" if IS_WINDOWS else "bin")


def python_exe() -> str:
    candidate = venv_bin() / ("python.exe" if IS_WINDOWS else "python")
    return str(candidate) if candidate.exists() else sys.executable


def find_tool(name: str) -> str | None:
    """Resolve a console script from the project venv first, then PATH."""
    for directory in (venv_bin(),):
        for suffix in (".exe", ".cmd", ""):
            candidate = directory / f"{name}{suffix}"
            if candidate.exists():
                return str(candidate)
    return shutil.which(name)


def run(cmd: Sequence[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> int:
    merged = {**os.environ, **(env or {})}
    # Console scripts from the project venv (shellcheck, actionlint, ...) win over system ones.
    merged["PATH"] = str(venv_bin()) + os.pathsep + merged.get("PATH", "")
    shown = " ".join(cmd)
    print(f"  $ {shown if len(shown) < 200 else shown[:197] + '...'}", flush=True)
    return subprocess.run(list(cmd), cwd=cwd, env=merged, check=False).returncode


def step(
    ctx: Context,
    name: str,
    cmd: Sequence[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
) -> Result:
    started = time.perf_counter()
    code = run(cmd, cwd=cwd, env=env)
    return ctx.add(
        Result(
            name,
            PASS if code == 0 else FAIL,
            "" if code == 0 else f"exit code {code}",
            time.perf_counter() - started,
        )
    )


def missing(ctx: Context, name: str, hint: str) -> Result:
    """A required tool is absent: SKIP locally (loudly), FAIL in CI."""
    status = FAIL if IS_CI else SKIP
    return ctx.add(Result(name, status, f"tool not available -- {hint}"))


def want_py() -> bool:
    return ONLY in {"all", "python"}


def want_web() -> bool:
    return ONLY in {"all", "web"}


def py_step(ctx: Context, name: str, module_args: Sequence[str], *, cwd: Path = ROOT) -> Result:
    if not want_py():  # out of scope for this run (NX_ONLY): not executed, not reported
        return Result(name, SKIP, "out of scope")
    return step(ctx, name, [python_exe(), "-m", *module_args], cwd=cwd)


def web_ready(ctx: Context, name: str) -> bool:
    if not want_web():
        return False
    if not (WEB / "package.json").exists():
        ctx.add(Result(name, SKIP, "apps/web has no package.json yet"))
        return False
    if shutil.which("npm") is None:
        missing(ctx, name, "install Node.js >= 22")
        return False
    if not (WEB / "node_modules").exists():
        missing(ctx, name, "run `npm ci --prefix apps/web` first")
        return False
    return True


def npm_step(ctx: Context, name: str, *args: str) -> Result:
    npm = shutil.which("npm") or "npm"
    return step(ctx, name, [npm, *args], cwd=WEB)


# --------------------------------------------------------------------------- tasks


def task_setup(ctx: Context) -> None:
    """Create .venv from the hash-pinned lock and install web dependencies."""
    if not (ROOT / ".venv").exists():
        step(ctx, "create venv", [sys.executable, "-m", "venv", str(ROOT / ".venv")])
    py = python_exe()
    step(
        ctx,
        "install pinned dev deps",
        [py, "-m", "pip", "install", "--require-hashes", "-r", "requirements/dev.txt"],
    )
    editable: list[str] = []
    for pkg in PY_PACKAGES:
        editable += ["-e", pkg]
    step(ctx, "install workspace packages", [py, "-m", "pip", "install", "--no-deps", *editable])
    if (WEB / "package.json").exists():
        if shutil.which("npm"):
            npm_step(ctx, "npm ci", "ci")
        else:
            missing(ctx, "npm ci", "install Node.js >= 22")


def task_lock(ctx: Context) -> None:
    """Re-resolve requirements/*.txt (exact versions + sha256 hashes)."""
    for name in ("prod", "dev"):
        py_step(
            ctx,
            f"pip-compile {name}",
            [
                "piptools",
                "compile",
                "--quiet",
                "--generate-hashes",
                "--strip-extras",
                "--allow-unsafe",
                "--output-file",
                f"requirements/{name}.txt",
                f"requirements/{name}.in",
            ],
        )


def task_lint(ctx: Context) -> None:
    py_step(ctx, "ruff check", ["ruff", "check", "."])
    py_step(ctx, "ruff format --check", ["ruff", "format", "--check", "."])
    if web_ready(ctx, "web lint"):
        npm_step(ctx, "web eslint", "run", "lint")
        npm_step(ctx, "web prettier", "run", "format:check")


def task_format(ctx: Context) -> None:
    py_step(ctx, "ruff fix", ["ruff", "check", "--fix", "."])
    py_step(ctx, "ruff format", ["ruff", "format", "."])
    if web_ready(ctx, "web format"):
        npm_step(ctx, "web prettier --write", "run", "format")


def task_typecheck(ctx: Context) -> None:
    py_step(ctx, "mypy --strict", ["mypy", *PY_SOURCES, "tools"])
    if web_ready(ctx, "web typecheck"):
        npm_step(ctx, "web tsc", "run", "typecheck")


def _pytest(ctx: Context, name: str, marker: str, extra: Sequence[str] = ()) -> Result:
    return py_step(ctx, name, ["pytest", "-m", marker, "-q", "--no-header", *extra])


COV_COLLECT = ["--cov", "--cov-report=", "--cov-fail-under=0"]  # gate runs once, in `test`


def task_test_unit(ctx: Context) -> None:
    _pytest(ctx, "pytest unit", "not contract and not integration", [*COV_COLLECT])
    if web_ready(ctx, "web unit tests"):
        npm_step(ctx, "web vitest (coverage gate)", "test")


def task_test_contract(ctx: Context) -> None:
    _pytest(ctx, "pytest contract", "contract", [*COV_COLLECT, "--cov-append"])
    if web_ready(ctx, "web api types drift"):
        npm_step(ctx, "web openapi types in sync", "run", "gen:api:check")


def task_test_integration(ctx: Context) -> None:
    if not os.environ.get("NEXORA_TEST_DATABASE_URL"):
        status = FAIL if IS_CI else SKIP
        ctx.add(
            Result(
                "pytest integration (postgres)",
                status,
                "NEXORA_TEST_DATABASE_URL not set -- integration tests were NOT executed",
            )
        )
        return
    _pytest(ctx, "pytest integration (postgres)", "integration")


def task_test(ctx: Context) -> None:
    """Unit + contract tests, then ONE coverage gate over both."""
    py_step(ctx, "coverage erase", ["coverage", "erase"])
    task_test_unit(ctx)
    task_test_contract(ctx)
    py_step(
        ctx,
        "python coverage gate (unit+contract)",
        ["coverage", "report", "--skip-covered"],  # fail_under is read from pyproject.toml
    )
    py_step(ctx, "coverage xml", ["coverage", "xml", "-o", ".nx/coverage.xml"])
    ctx.add(
        Result(
            "integration tests",
            SKIP,
            "not part of `test`; run `make test-integration` (needs PostgreSQL)",
        )
    )


def _load_checks() -> list[ModuleType]:
    modules: list[ModuleType] = []
    sys.path.insert(0, str(ROOT / "tools"))
    for path in sorted((ROOT / "tools" / "checks").glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"checks.{path.stem}", path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            modules.append(module)
    return modules


def task_validate(ctx: Context) -> None:
    """Static validation: architecture boundaries, repo policy, YAML, deploy config."""
    if not want_py():
        return
    importlinter = find_tool("lint-imports")
    if importlinter:
        step(ctx, "import-linter (architecture boundaries)", [importlinter])
    else:
        missing(ctx, "import-linter", "pip install -r requirements/dev.txt")

    yamllint = find_tool("yamllint")
    if yamllint:
        step(
            ctx,
            "yamllint",
            [
                yamllint,
                "--strict",
                "-c",
                ".yamllint.yaml",
                ".github",
                "deploy",
                "contracts",
                ".yamllint.yaml",
            ],
        )
    else:
        missing(ctx, "yamllint", "pip install -r requirements/dev.txt")

    actionlint = find_tool("actionlint")
    if actionlint and (ROOT / ".github" / "workflows").exists():
        step(ctx, "actionlint (GitHub workflows)", [actionlint])
    elif not actionlint:
        missing(ctx, "actionlint", "pip install -r requirements/dev.txt")

    for module in _load_checks():
        name = str(getattr(module, "NAME", module.__name__))
        started = time.perf_counter()
        problems: list[str] = list(getattr(module, "run")(ROOT))  # noqa: B009
        if problems:
            ctx.add(
                Result(
                    f"check:{name}",
                    FAIL,
                    f"{len(problems)} problem(s)",
                    time.perf_counter() - started,
                )
            )
            for problem in problems:
                print(f"       - {problem}")
        else:
            ctx.add(Result(f"check:{name}", PASS, "", time.perf_counter() - started))
        optional = getattr(module, "optional_steps", None)
        if optional is not None:
            for label, status, messages in optional(ROOT):
                final = FAIL if (status == "skip" and IS_CI) else status.upper()
                ctx.add(Result(f"{name}:{label}", final, "; ".join(messages)))


def task_build(ctx: Context) -> None:
    """Build distributable artifacts: python wheels and the web bundle (no Docker)."""
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    for pkg in PY_PACKAGES:
        py_step(ctx, f"wheel {pkg}", ["build", "--wheel", "--outdir", str(out), str(ROOT / pkg)])
    if web_ready(ctx, "web build"):
        npm_step(ctx, "web vite build", "run", "build")


def _docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


def _git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short=12", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() or "local"


def task_docker_build(ctx: Context) -> None:
    """Build container images. Needs a running Docker daemon (CI always has one)."""
    if not _docker_ready():
        missing(ctx, "docker build", "Docker daemon not running -- images are verified in CI")
        return
    sha = os.environ.get("GITHUB_SHA", _git_sha())[:12]
    images = {
        "control-plane": "infra/docker/control-plane.Dockerfile",
        "web": "infra/docker/web.Dockerfile",
    }
    for name, dockerfile in images.items():
        step(
            ctx,
            f"docker build {name}",
            [
                "docker",
                "build",
                "-f",
                dockerfile,
                "-t",
                f"nexora/{name}:{sha}",
                "--build-arg",
                f"GIT_SHA={sha}",
                ".",
            ],
        )


def task_security_check(ctx: Context) -> None:
    py_step(
        ctx,
        "bandit (shipped python code)",
        ["bandit", "-q", "-c", "pyproject.toml", "-r", "packages", "services", "sdk"],
    )
    py_step(
        ctx,
        "bandit (dev tooling; subprocess use is by design, static argv, no shell)",
        [
            "bandit",
            "-q",
            "-c",
            "pyproject.toml",
            "-r",
            "tools",
            "--skip",
            "B101,B404,B603,B607,B105",
        ],
    )
    py_step(
        ctx,
        "pip-audit (python deps, prod lock)",
        [
            "pip_audit",
            "--no-deps",
            "--disable-pip",
            "--require-hashes",
            "-r",
            "requirements/prod.txt",
            "--progress-spinner",
            "off",
        ],
    )
    if web_ready(ctx, "npm audit"):
        npm_step(
            ctx, "npm audit (runtime deps, high+)", "audit", "--omit=dev", "--audit-level=high"
        )
    hook = find_tool("detect-secrets-hook") if want_py() else None
    if not want_py():
        pass
    elif hook:
        files = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.split()
        if files:
            started = time.perf_counter()
            codes = [
                run([hook, "--baseline", ".secrets.baseline", *files[i : i + 80]])
                for i in range(0, len(files), 80)  # keep the command line short on Windows
            ]
            ctx.add(
                Result(
                    "detect-secrets (vs .secrets.baseline)",
                    PASS if not any(codes) else FAIL,
                    "" if not any(codes) else "new potential secret(s) found",
                    time.perf_counter() - started,
                )
            )
        else:
            ctx.add(Result("detect-secrets", SKIP, "no tracked files yet (git add first)"))
    else:
        missing(ctx, "detect-secrets", "pip install -r requirements/dev.txt")
    ctx.add(
        Result(
            "trivy / container scan / SBOM",
            SKIP,
            "CI-only (needs built images): see .github/workflows/images.yml",
        )
    )


def task_openapi_update(ctx: Context) -> None:
    """Regenerate contracts/openapi/control-plane.v1.json from the code (then commit it)."""
    target = ROOT / "contracts" / "openapi" / "control-plane.v1.json"
    proc = subprocess.run(
        [python_exe(), "-m", "nexora_control_plane.openapi"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr)
        ctx.add(Result("openapi-update", FAIL, "generator failed"))
        return
    target.write_text(proc.stdout, encoding="utf-8", newline="\n")
    ctx.add(Result("openapi-update", PASS, str(target.relative_to(ROOT))))
    if (WEB / "node_modules").exists():
        npm_step(ctx, "regenerate web api types", "run", "gen:api")


def task_check(ctx: Context) -> None:
    """Everything a pull request must pass (no Docker, no network services)."""
    for task in (
        task_lint,
        task_typecheck,
        task_test,
        task_validate,
        task_build,
        task_security_check,
    ):
        task(ctx)


TASKS: dict[str, Callable[[Context], None]] = {
    "setup": task_setup,
    "lock": task_lock,
    "lint": task_lint,
    "format": task_format,
    "typecheck": task_typecheck,
    "test": task_test,
    "test-unit": task_test_unit,
    "test-contract": task_test_contract,
    "test-integration": task_test_integration,
    "validate": task_validate,
    "build": task_build,
    "docker-build": task_docker_build,
    "security-check": task_security_check,
    "openapi-update": task_openapi_update,
    "check": task_check,
}


def summarize(results: Iterable[Result]) -> int:
    results = list(results)
    print("\n" + "=" * 78)
    print(f"{'STEP':<52} {'STATUS':<7} {'TIME':>7}")
    print("-" * 78)
    for r in results:
        print(f"{r.name[:51]:<52} {r.status:<7} {r.seconds:>6.1f}s")
    failed = [r for r in results if r.status == FAIL]
    skipped = [r for r in results if r.status == SKIP]
    print("-" * 78)
    print(
        f"passed={sum(r.status == PASS for r in results)} failed={len(failed)} "
        f"skipped={len(skipped)} ci={IS_CI}"
    )
    for r in skipped:
        print(f"  SKIPPED (NOT verified here): {r.name} -- {r.detail}")
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nx", description="NEXORA task runner")
    parser.add_argument("task", choices=sorted(TASKS))
    args = parser.parse_args(argv)
    ctx = Context()
    TASKS[args.task](ctx)
    return summarize(ctx.results)


if __name__ == "__main__":
    raise SystemExit(main())
