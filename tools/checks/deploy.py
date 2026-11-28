"""Static and tool-backed validation of the deployment assets (compose, Kubernetes, Helm).

Interface used by ``tools/nx.py validate``:

* ``NAME``                 -- check identifier;
* ``run(root)``            -- offline static checks (stdlib + PyYAML); returns problem strings,
                              an empty list means PASS;
* ``optional_steps(root)`` -- steps that need external tools (docker compose, helm, kubectl).
                              Returns ``(label, status, messages)`` with status in
                              ``{"pass", "fail", "skip"}``. A missing tool is ``skip`` locally and
                              ``fail`` when ``CI`` is set, so CI can never pass silently.

CLI: ``python tools/checks/deploy.py [--require-substituted DIR]``. The second form is the
release guard: it fails while any release placeholder is still present under DIR.

What these checks prove: that the committed assets are internally consistent and follow the
policy (pinned images, no literal secrets, hardened workloads). They do NOT prove that an image
builds or that a cluster accepts the manifests; that is verified in CI / on the target.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

NAME = "deploy"

PLACEHOLDERS = ("REPLACE_WITH_RELEASE_SHA", "REPLACE_WITH_OWNER")
PLACEHOLDER_ALLOWED = re.compile(r"^deploy/kubernetes/overlays/[^/]+/kustomization\.yaml$")
SCANNED_ROOTS = ("deploy", "infra/docker")
FLOATING_TAGS = frozenset(
    {"latest", "stable", "lts", "main", "master", "edge", "nightly", "current", "dev", "slim"}
)
WORKLOAD_KINDS = ("Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob")
SECRET_KEY_RE = re.compile(
    r"(password|passwd|secret|token|credential|api_?key|private_?key|access_?key)", re.IGNORECASE
)
STRUCTURAL_KEY_RE = re.compile(r"(name|ref|keyref)$", re.IGNORECASE)
STRUCTURAL_KEYS = frozenset({"secretKey"})
SKIPPED_SUBTREES = frozenset({"remoteRef", "remoteKeys", "secretStoreRef", "externalSecret"})
URL_CREDENTIAL_RE = re.compile(r"://[^/\s:@$]+:(?!\$\{)[^/\s@]+@")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
ENV_VAR_TAG_RE = re.compile(r"\$\{(\w+)(?::?[-?+=].*)?\}", re.DOTALL)
ALLOWED_TAG_VARS = frozenset({"NEXORA_IMAGE_TAG"})
SHA_TAG_RE = re.compile(r"[0-9a-f]{7,64}")
PATCH_VERSIONING = re.compile(r"\d+\.\d+\.\d+")
MAJOR_MINOR_VERSIONING = re.compile(r"\d+\.\d+")
# Images whose releases are versioned major.minor (a minor release IS the patch level).
MAJOR_MINOR_IMAGES = frozenset({"postgres"})
COMPOSE_DUMMY_ENV = {
    "NEXORA_IMAGE_REGISTRY": "ghcr.io/example/nexora-platform",
    "NEXORA_IMAGE_TAG": "0123456789abcdef",
    "NEXORA_POSTGRES_PASSWORD": "placeholder",
    "NEXORA_API_TOKEN": "placeholder",
}
HELM_SET = ("--set", "image.registry=ghcr.io/example/nexora-platform", "--set", "image.tag=0123abc")
TOOL_TIMEOUT_SECONDS = 180

Doc = dict[str, Any]


# ----------------------------------------------------------------------------- helpers


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _scanned_files(root: Path) -> Iterator[Path]:
    for sub in SCANNED_ROOTS:
        base = root / sub
        if base.is_dir():
            yield from (p for p in sorted(base.rglob("*")) if p.is_file())


def _is_helm_template(root: Path, path: Path) -> bool:
    return "templates" in path.relative_to(root).parts and "helm" in path.relative_to(root).parts


def _load_yaml_docs(path: Path) -> list[Doc]:
    docs = [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d is not None]
    return [d for d in docs if isinstance(d, dict)]


def _walk(node: Any, path: str = "") -> Iterator[tuple[str, Any, str]]:
    """Yield (key, value, dotted-path) for every mapping entry, depth first."""
    if isinstance(node, dict):
        for key, value in node.items():
            sub = f"{path}.{key}" if path else str(key)
            yield str(key), value, sub
            if str(key) not in SKIPPED_SUBTREES:
                yield from _walk(value, sub)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk(item, f"{path}[{index}]")


# ----------------------------------------------------------------------------- images


def image_problem(ref: str) -> str | None:
    """Policy for one image reference; None when acceptable."""
    if "@sha256:" in ref:
        return None
    name_part = ref.rsplit("/", 1)[-1]
    if ":" not in name_part:
        return f"image '{ref}' has no tag or digest"
    tag = name_part.split(":", 1)[1]
    var = ENV_VAR_TAG_RE.fullmatch(tag)
    if var:
        if var.group(1) in ALLOWED_TAG_VARS:
            return None
        return (
            f"image '{ref}' uses variable ${{{var.group(1)}}} as tag "
            "(only NEXORA_IMAGE_TAG allowed)"
        )
    if "${" in tag or "{{" in tag:
        return f"image '{ref}' has a templated tag"
    if tag.lower() in FLOATING_TAGS:
        return f"image '{ref}' uses a floating tag; pin an exact version or a digest"
    if SHA_TAG_RE.fullmatch(tag):
        return None  # immutable CI tag (git SHA)
    base = name_part.split(":", 1)[0]
    pattern = MAJOR_MINOR_VERSIONING if base in MAJOR_MINOR_IMAGES else PATCH_VERSIONING
    if not pattern.search(tag):
        return f"image '{ref}' is not pinned to an exact version or digest"
    return None


def _dockerfile_problems(rel: str, text: str) -> list[str]:
    problems: list[str] = []
    stages: set[str] = set()
    for line_no, raw in enumerate(text.splitlines(), start=1):
        parts = raw.strip().split()
        if not parts or parts[0].upper() != "FROM":
            continue
        args = [p for p in parts[1:] if not p.startswith("--")]
        image = args[0] if args else ""
        if "AS" in (a.upper() for a in args[1:]):
            stages.add(args[-1])
        if image in stages or image == "scratch":
            continue
        if "$" in image:
            problems.append(f"{rel}:{line_no}: FROM uses a build variable; pin the image literally")
            continue
        problem = image_problem(image)
        if problem:
            problems.append(f"{rel}:{line_no}: {problem}")
    return problems


def _image_refs(doc: Doc) -> Iterator[str]:
    for key, value, _ in _walk(doc):
        if key == "image" and isinstance(value, str):
            yield value


# ----------------------------------------------------------------------------- secrets


def _value_is_placeholder(value: str) -> bool:
    return value == "" or "${" in value or value.startswith("CHANGE_ME")


def _secret_problems(rel: str, doc: Any) -> list[str]:
    problems: list[str] = []
    for key, value, dotted in _walk(doc):
        if not isinstance(value, str):
            continue
        if URL_CREDENTIAL_RE.search(value):
            problems.append(f"{rel}: {dotted} embeds literal credentials in a URL")
        if (
            SECRET_KEY_RE.search(key)
            and key not in STRUCTURAL_KEYS
            and not STRUCTURAL_KEY_RE.search(key)
            and not _value_is_placeholder(value)
        ):
            problems.append(f"{rel}: {dotted} looks like a literal secret; use a variable or ref")
    # compose list-style environment: ["KEY=value"], k8s env: [{name: X, value: Y}]
    for key, value, dotted in _walk(doc):
        if key == "environment" and isinstance(value, list):
            for item in value:
                if isinstance(item, str) and "=" in item:
                    name, _, val = item.partition("=")
                    if SECRET_KEY_RE.search(name) and not _value_is_placeholder(val):
                        problems.append(f"{rel}: {dotted} sets literal secret {name}")
        if key == "env" and isinstance(value, list):
            for item in value:
                if (
                    isinstance(item, dict)
                    and isinstance(item.get("name"), str)
                    and isinstance(item.get("value"), str)
                    and SECRET_KEY_RE.search(item["name"])
                    and not _value_is_placeholder(item["value"])
                ):
                    problems.append(f"{rel}: {dotted} sets literal secret {item['name']}")
    return problems


def _text_problems(rel: str, text: str) -> list[str]:
    problems: list[str] = []
    if PRIVATE_KEY_RE.search(text):
        problems.append(f"{rel}: contains a private key block")
    if AWS_KEY_RE.search(text):
        problems.append(f"{rel}: contains an AWS access key id")
    if rel.endswith((".env.example", ".env")):
        for line_no, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, val = line.partition("=")
            if SECRET_KEY_RE.search(name) and val and not val.startswith("CHANGE_ME"):
                problems.append(f"{rel}:{line_no}: {name} must be empty or start with CHANGE_ME")
    return problems


# ----------------------------------------------------------------------------- kubernetes


def _pod_spec(doc: Doc) -> Doc | None:
    kind = doc.get("kind")
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        return None
    try:
        if kind in ("Deployment", "StatefulSet", "DaemonSet", "Job"):
            result = spec["template"]["spec"]
        elif kind == "CronJob":
            result = spec["jobTemplate"]["spec"]["template"]["spec"]
        else:
            return None
    except (KeyError, TypeError):
        return None
    return result if isinstance(result, dict) else None


def workload_problems(where: str, doc: Doc) -> list[str]:
    """Hardening policy for one Kubernetes workload document."""
    pod = _pod_spec(doc)
    if pod is None:
        return []
    kind = str(doc.get("kind"))
    name = str(doc.get("metadata", {}).get("name", "?"))
    tag = f"{where}: {kind}/{name}"
    problems: list[str] = []
    pod_sc = pod.get("securityContext") or {}
    if pod.get("automountServiceAccountToken") is not False:
        problems.append(f"{tag}: automountServiceAccountToken must be false")
    containers = [*(pod.get("initContainers") or []), *(pod.get("containers") or [])]
    if not containers:
        problems.append(f"{tag}: no containers")
    for container in containers:
        cname = f"{tag} container '{container.get('name', '?')}'"
        sc = container.get("securityContext") or {}
        if not (pod_sc.get("runAsNonRoot") or sc.get("runAsNonRoot")):
            problems.append(f"{cname}: runAsNonRoot must be true")
        seccomp = (sc.get("seccompProfile") or pod_sc.get("seccompProfile") or {}).get("type")
        if seccomp != "RuntimeDefault":
            problems.append(f"{cname}: seccompProfile must be RuntimeDefault")
        if sc.get("allowPrivilegeEscalation") is not False:
            problems.append(f"{cname}: allowPrivilegeEscalation must be false")
        if sc.get("readOnlyRootFilesystem") is not True:
            problems.append(f"{cname}: readOnlyRootFilesystem must be true")
        if "ALL" not in ((sc.get("capabilities") or {}).get("drop") or []):
            problems.append(f"{cname}: capabilities.drop must include ALL")
        resources = container.get("resources") or {}
        for section in ("requests", "limits"):
            values = resources.get(section) or {}
            for resource in ("cpu", "memory"):
                if resource not in values:
                    problems.append(f"{cname}: resources.{section}.{resource} is required")
        if kind in ("Deployment", "StatefulSet", "DaemonSet") and container.get("ports"):
            for probe in ("livenessProbe", "readinessProbe"):
                if probe not in container:
                    problems.append(f"{cname}: {probe} is required")
    return problems


def _k8s_problems(root: Path) -> list[str]:
    problems: list[str] = []
    base = root / "deploy" / "kubernetes"
    if not base.is_dir():
        return ["deploy/kubernetes is missing"]
    for path in sorted(base.rglob("*.yaml")):
        rel = _rel(root, path)
        for doc in _load_yaml_docs(path):
            if doc.get("kind") == "Secret":
                problems.append(f"{rel}: kind Secret must not be committed; use ExternalSecret")
            problems.extend(workload_problems(rel, doc))
            if doc.get("kind") in WORKLOAD_KINDS:
                for ref in _image_refs(doc):
                    problem = image_problem(ref)
                    if problem:
                        problems.append(f"{rel}: {problem}")
    for overlay in sorted((base / "overlays").glob("*/kustomization.yaml")):
        rel = _rel(root, overlay)
        for doc in _load_yaml_docs(overlay):
            images = doc.get("images") or []
            if not any(str(i.get("newTag")) == PLACEHOLDERS[0] for i in images):
                problems.append(f"{rel}: release placeholder {PLACEHOLDERS[0]} is missing")
            if not any(PLACEHOLDERS[1] in str(i.get("newName")) for i in images):
                problems.append(f"{rel}: release placeholder {PLACEHOLDERS[1]} is missing")
            for image in images:
                tag = str(image.get("newTag", ""))
                if tag.lower() in FLOATING_TAGS or tag == "":
                    problems.append(f"{rel}: images.newTag '{tag}' is floating or empty")
    return problems


# ----------------------------------------------------------------------------- compose / helm


def _compose_problems(root: Path) -> list[str]:
    problems: list[str] = []
    path = root / "deploy" / "compose" / "docker-compose.yml"
    if not path.is_file():
        return ["deploy/compose/docker-compose.yml is missing"]
    rel = _rel(root, path)
    doc = _load_yaml_docs(path)[0]
    services = doc.get("services") or {}
    for name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        if svc.get("ports") and name != "web":
            problems.append(f"{rel}: service '{name}' publishes host ports; only 'web' may")
        if svc.get("privileged") or svc.get("network_mode") == "host":
            problems.append(f"{rel}: service '{name}' is privileged or uses host networking")
        for volume in svc.get("volumes") or []:
            if "docker.sock" in str(volume):
                problems.append(f"{rel}: service '{name}' mounts the docker socket")
        long_running = svc.get("restart") not in (None, "no", False)
        if long_running and "healthcheck" not in svc:
            problems.append(f"{rel}: long-running service '{name}' has no healthcheck")
    for required in ("postgres", "migrate", "control-plane", "web"):
        if required not in services:
            problems.append(f"{rel}: service '{required}' is missing")
    return problems


def _helm_problems(root: Path) -> list[str]:
    chart = root / "deploy" / "helm" / "nexora"
    problems: list[str] = []
    if not chart.is_dir():
        return ["deploy/helm/nexora is missing"]
    for required in ("Chart.yaml", "values.yaml", "values.schema.json", "templates/_helpers.tpl"):
        if not (chart / required).is_file():
            problems.append(f"deploy/helm/nexora/{required} is missing")
    values_path = chart / "values.yaml"
    if values_path.is_file():
        values = yaml.safe_load(values_path.read_text(encoding="utf-8")) or {}
        image = values.get("image") or {}
        if image.get("tag", None) != "" or image.get("registry", None) != "":
            problems.append("helm values.yaml: image.registry/image.tag must default to empty")
        for part in ("controlPlane", "web"):
            section = values.get(part) or {}
            sc = section.get("securityContext") or {}
            if (
                sc.get("readOnlyRootFilesystem") is not True
                or sc.get("allowPrivilegeEscalation") is not False
            ):
                problems.append(f"helm values.yaml: {part}.securityContext is not hardened")
            if "ALL" not in ((sc.get("capabilities") or {}).get("drop") or []):
                problems.append(f"helm values.yaml: {part}.securityContext must drop ALL")
            if (section.get("podSecurityContext") or {}).get("runAsNonRoot") is not True:
                problems.append(f"helm values.yaml: {part}.podSecurityContext.runAsNonRoot")
    helpers = chart / "templates" / "_helpers.tpl"
    if helpers.is_file():
        text = helpers.read_text(encoding="utf-8")
        if "required" not in text or "latest" not in text:
            problems.append("helm _helpers.tpl must `required` the tag and reject latest")
    return problems


# ----------------------------------------------------------------------------- run


def release_placeholder_problems(root: Path, target: Path) -> list[str]:
    """Release guard: no placeholder may remain under ``target``."""
    problems: list[str] = []
    files = [target] if target.is_file() else sorted(p for p in target.rglob("*") if p.is_file())
    for path in files:
        if path.suffix not in {".yaml", ".yml", ".json", ".tpl"}:
            continue
        text = path.read_text(encoding="utf-8")
        for placeholder in PLACEHOLDERS:
            if placeholder in text:
                problems.append(f"{_rel(root, path)}: unsubstituted placeholder {placeholder}")
    return problems


def run(root: Path) -> list[str]:
    problems: list[str] = []
    for path in _scanned_files(root):
        rel = _rel(root, path)
        if path.suffix in {".png", ".jpg", ".ico", ".woff2", ".tgz"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        problems.extend(_text_problems(rel, text))
        if path.suffix in {".yaml", ".yml", ".json", ".tpl"} and not PLACEHOLDER_ALLOWED.match(rel):
            for placeholder in PLACEHOLDERS:
                if placeholder in text:
                    problems.append(f"{rel}: release placeholder {placeholder} not allowed here")
        if path.name.endswith("Dockerfile") or path.suffix == ".Dockerfile":
            problems.extend(_dockerfile_problems(rel, text))
        elif path.suffix in {".yaml", ".yml"} and not _is_helm_template(root, path):
            try:
                docs = _load_yaml_docs(path)
            except yaml.YAMLError as exc:
                problems.append(f"{rel}: invalid YAML: {exc}")
                continue
            for doc in docs:
                problems.extend(_secret_problems(rel, doc))
                if "compose" in rel:
                    for ref in _image_refs(doc):
                        problem = image_problem(ref)
                        if problem:
                            problems.append(f"{rel}: {problem}")
        elif path.suffix == ".json":
            try:
                json.loads(text)
            except ValueError as exc:
                problems.append(f"{rel}: invalid JSON: {exc}")
    problems.extend(_k8s_problems(root))
    problems.extend(_compose_problems(root))
    problems.extend(_helm_problems(root))
    return sorted(set(problems))


# ----------------------------------------------------------------------------- tool-backed steps

Step = tuple[str, str, list[str]]


def _ci_mode() -> bool:
    return os.environ.get("CI", "").lower() in {"1", "true", "yes"}


def _missing_tool(label: str, tool: str) -> Step:
    status = "fail" if _ci_mode() else "skip"
    hint = "CI requires it" if _ci_mode() else "not installed locally; enforced in CI"
    return (label, status, [f"`{tool}` not found on PATH ({hint})"])


def _exec(
    label: str,
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    expect_failure_containing: str | tuple[str, ...] | None = None,
) -> Step:
    full_env = {**os.environ, **(env or {})}
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=full_env,
            capture_output=True,
            text=True,
            timeout=TOOL_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (label, "fail", [f"{type(exc).__name__}: {exc}"])
    output = (proc.stdout + proc.stderr).strip()
    tail = output.splitlines()[-8:]
    if expect_failure_containing is not None:
        needles = (
            (expect_failure_containing,)
            if isinstance(expect_failure_containing, str)
            else expect_failure_containing
        )
        if proc.returncode != 0 and any(needle in output for needle in needles):
            return (label, "pass", [])
        return (
            label,
            "fail",
            [f"expected failure containing '{expect_failure_containing}'", *tail],
        )
    if proc.returncode == 0:
        return (label, "pass", [])
    return (label, "fail", tail)


def optional_steps(root: Path) -> list[Step]:
    steps: list[Step] = []
    compose_dir = root / "deploy" / "compose"

    docker = shutil.which("docker")
    if docker is None:
        steps.append(_missing_tool("docker compose config", "docker"))
    else:
        for label, files in (
            ("docker compose config (release)", ["docker-compose.yml"]),
            (
                "docker compose config (dev override)",
                ["docker-compose.yml", "docker-compose.dev.yml"],
            ),
        ):
            argv = [docker, "compose"]
            for name in files:
                argv += ["-f", name]
            steps.append(
                _exec(label, [*argv, "config", "-q"], cwd=compose_dir, env=COMPOSE_DUMMY_ENV)
            )
        steps.append(
            _exec(
                "docker compose rejects missing secrets",
                [docker, "compose", "-f", "docker-compose.yml", "config", "-q"],
                cwd=compose_dir,
                env=dict.fromkeys(COMPOSE_DUMMY_ENV, ""),
                expect_failure_containing="required variable",
            )
        )

    helm = shutil.which("helm")
    chart = root / "deploy" / "helm" / "nexora"
    if helm is None:
        steps.append(_missing_tool("helm lint/template", "helm"))
    else:
        steps.append(_exec("helm lint", [helm, "lint", str(chart), *HELM_SET], cwd=root))
        steps.append(
            _exec(
                "helm template (all optional features)",
                [
                    helm,
                    "template",
                    "rel",
                    str(chart),
                    *HELM_SET,
                    "--set",
                    "ingress.enabled=true",
                    "--set",
                    "ingress.host=nexora.example.com",
                    "--set",
                    "secrets.externalSecret.enabled=true",
                    "--set",
                    "autoscaling.enabled=true",
                    "--set",
                    "serviceMonitor.enabled=true",
                ],
                cwd=root,
            )
        )
        steps.append(
            _exec(
                "helm template refuses a missing image tag",
                [helm, "template", "rel", str(chart), "--set", "image.registry=ghcr.io/x/y"],
                cwd=root,
                expect_failure_containing="image.tag",
            )
        )
        steps.append(
            _exec(
                "helm template refuses the latest tag",
                [
                    helm,
                    "template",
                    "rel",
                    str(chart),
                    "--set",
                    "image.registry=ghcr.io/x/y",
                    "--set",
                    "image.tag=latest",
                ],
                cwd=root,
                # schema errors name the JSON pointer (/image/tag); the template helper says image.tag
                expect_failure_containing=("image.tag", "/image/tag"),
            )
        )

    kubectl = shutil.which("kubectl")
    if kubectl is None:
        steps.append(_missing_tool("kubectl kustomize", "kubectl"))
    else:
        for target in ("base", "overlays/staging", "overlays/production"):
            label = f"kubectl kustomize {target}"
            path = root / "deploy" / "kubernetes" / target
            step = _exec(label, [kubectl, "kustomize", str(path)], cwd=root)
            if step[1] == "pass":
                step = _rendered_workload_step(label, kubectl, path, root)
            steps.append(step)
    return steps


def _rendered_workload_step(label: str, kubectl: str, path: Path, root: Path) -> Step:
    """Re-apply the hardening policy to the manifests AFTER overlays/patches were rendered."""
    proc = subprocess.run(
        [kubectl, "kustomize", str(path)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=TOOL_TIMEOUT_SECONDS,
        check=False,
    )
    problems: list[str] = []
    for doc in yaml.safe_load_all(proc.stdout):
        if isinstance(doc, dict):
            problems.extend(workload_problems(f"rendered {path.name}", doc))
    if problems:
        return (label, "fail", problems[:8])
    return (label, "pass", [])


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(__file__).resolve().parents[2]
    if args[:1] == ["--require-substituted"]:
        if len(args) != 2:
            sys.stderr.write("usage: deploy.py --require-substituted DIR\n")
            return 2
        problems = release_placeholder_problems(root, Path(args[1]).resolve())
        for problem in problems:
            sys.stdout.write(f"FAIL {problem}\n")
        return 1 if problems else 0
    problems = run(root)
    for problem in problems:
        sys.stdout.write(f"FAIL {problem}\n")
    for label, status, messages in optional_steps(root):
        sys.stdout.write(f"{status.upper():5} {label}\n")
        for message in messages:
            sys.stdout.write(f"        {message}\n")
        if status == "fail":
            problems.append(label)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
