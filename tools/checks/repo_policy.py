"""Repository policy checks executed by `make validate`.

Each rule mirrors a mandatory engineering restriction of the NEXORA directive. A rule that
cannot be evaluated is a failure, never a silent pass.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

NAME = "repo-policy"

REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "NOTICE",
    "docs/INSTALL.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".github/CODEOWNERS",
    ".secrets.baseline",
    "docs/architecture/overview.md",
    "docs/architecture/server-deployment.md",
    "docs/engineering/conventions.md",
    "docs/adr/README.md",
    "docs/roadmap.md",
    "docs/status/PROJECT_STATUS.md",
    "docs/status/TEST_EVIDENCE.md",
    "requirements/prod.txt",
    "requirements/dev.txt",
    "contracts/openapi/control-plane.v1.json",
)

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SECRET_PATTERNS = {
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    "AWS access key id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
}
WORKSTATION_PATH_RE = re.compile(
    r"[A-Za-z]:\\Users\\|/Users/[A-Za-z0-9_.-]+/|/home/[a-z][a-z0-9_-]+/"
)
SOURCE_ROOTS = ("packages", "services", "sdk")
SCAN_SUFFIXES = {".py", ".yml", ".yaml", ".toml", ".json", ".ts", ".tsx", ".md", ".sh", ".cfg", ""}
SELF = Path(__file__).name


def tracked_files(root: Path) -> list[Path]:
    """Files git knows about (or would add); falls back to a directory walk without git."""
    try:
        proc = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        return [root / line for line in proc.stdout.splitlines() if (root / line).is_file()]
    except (OSError, subprocess.CalledProcessError):
        skip = {".git", "node_modules", ".venv", "dist", "build"}
        return [p for p in root.rglob("*") if p.is_file() and not skip.intersection(p.parts)]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_required_files(root: Path) -> list[str]:
    return [f"required file missing: {rel}" for rel in REQUIRED_FILES if not (root / rel).exists()]


def check_workflows(root: Path) -> list[str]:
    problems: list[str] = []
    for path in sorted((root / ".github" / "workflows").glob("*.y*ml")):
        rel = path.relative_to(root).as_posix()
        try:
            doc = yaml.safe_load(_read(path))
        except yaml.YAMLError as exc:
            problems.append(f"{rel}: invalid YAML ({exc})")
            continue
        if not isinstance(doc, dict):
            problems.append(f"{rel}: workflow is not a mapping")
            continue
        if "permissions" not in doc:
            problems.append(f"{rel}: top-level `permissions:` is required (least privilege)")
        for job_name, job in (doc.get("jobs") or {}).items():
            uses = [job.get("uses")] if isinstance(job, dict) else []
            for step in (job.get("steps") or []) if isinstance(job, dict) else []:
                uses.append(step.get("uses"))
            for ref in filter(None, uses):
                if ref.startswith("./"):
                    continue
                _, _, version = ref.partition("@")
                if not SHA_RE.match(version):
                    problems.append(
                        f"{rel} job '{job_name}': action '{ref}' must be pinned to a commit SHA"
                    )
        text = _read(path)
        if re.search(r"\bpull_request_target\b", text):
            problems.append(f"{rel}: pull_request_target is forbidden (untrusted code + secrets)")
    return problems


def check_adr_index(root: Path) -> list[str]:
    adr_dir = root / "docs" / "adr"
    index = adr_dir / "README.md"
    if not index.exists():
        return ["docs/adr/README.md missing"]
    listing = _read(index)
    problems: list[str] = []
    adrs = sorted(p for p in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))
    if not adrs:
        problems.append("no ADRs found in docs/adr")
    for adr in adrs:
        if adr.name not in listing:
            problems.append(f"{adr.name} is not listed in docs/adr/README.md")
        if not re.search(r"^Status:\s*(Proposed|Accepted|Superseded|Deprecated)", _read(adr), re.M):
            problems.append(f"{adr.name}: missing `Status:` line")
    return problems


def check_adapter_contract_docs(root: Path) -> list[str]:
    from nexora_core.engines import EngineKind

    return [
        f"contracts/adapters/{kind.value}.md missing (every EngineKind needs a contract doc)"
        for kind in EngineKind
        if not (root / "contracts" / "adapters" / f"{kind.value}.md").exists()
    ]


def check_lockfiles(root: Path) -> list[str]:
    problems: list[str] = []
    for name in ("prod", "dev"):
        lock = root / "requirements" / f"{name}.txt"
        if lock.exists() and "--hash=sha256:" not in _read(lock):
            problems.append(
                f"requirements/{name}.txt has no hashes (compile with --generate-hashes)"
            )
    if (root / "apps" / "web" / "package.json").exists() and not (
        root / "apps" / "web" / "package-lock.json"
    ).exists():
        problems.append("apps/web/package-lock.json missing (dependencies must be locked)")
    return problems


def check_no_secrets_or_workstation_paths(root: Path) -> list[str]:
    problems: list[str] = []
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if (
            path.name == SELF
            or path.suffix not in SCAN_SUFFIXES
            or "package-lock" in path.name
            or rel.startswith("tools/tests/")  # fixtures that must contain fake secrets
        ):
            continue
        name = path.name
        if name == ".env" or (name.startswith(".env.") and not name.endswith(".example")):
            problems.append(f"{rel}: environment file must not be committed")
            continue
        text = _read(path)
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                problems.append(f"{rel}: looks like a committed {label}")
        in_source = rel.split("/", 1)[0] in SOURCE_ROOTS or rel.startswith(("deploy/", "infra/"))
        if in_source and "/tests/" not in rel and WORKSTATION_PATH_RE.search(text):
            problems.append(f"{rel}: contains a workstation-specific path")
    return problems


def check_no_localhost_in_python_sources(root: Path) -> list[str]:
    """Application code must not hardcode development addresses."""
    problems: list[str] = []
    for top in SOURCE_ROOTS:
        for path in (root / top).rglob("src/**/*.py"):
            text = _read(path)
            if re.search(r"""["'](?:https?://)?(?:localhost|127\.0\.0\.1)[:/"']""", text):
                problems.append(
                    f"{path.relative_to(root).as_posix()}: hardcoded localhost/127.0.0.1 address"
                )
    return problems


def check_line_endings(root: Path) -> list[str]:
    """Text files must use LF (Windows tools sometimes write CRLF; it breaks linters and shells)."""
    problems: list[str] = []
    for path in tracked_files(root):
        if path.suffix in {".ps1", ".cmd", ".png", ".jpg", ".ico", ".woff2", ".whl"}:
            continue
        data = path.read_bytes()
        if b"\r\n" in data and b"\0" not in data:
            problems.append(f"{path.relative_to(root).as_posix()}: CRLF line endings (use LF)")
    return problems


def run(root: Path) -> list[str]:
    problems: list[str] = []
    for rule in (
        check_required_files,
        check_workflows,
        check_adr_index,
        check_adapter_contract_docs,
        check_lockfiles,
        check_no_secrets_or_workstation_paths,
        check_no_localhost_in_python_sources,
        check_line_endings,
    ):
        problems += rule(root)
    return problems
