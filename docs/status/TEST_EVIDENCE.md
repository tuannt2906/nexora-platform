# Test evidence

Environment of the recorded run: Windows 11 workstation, Python 3.11.9, Node 24, Git Bash/PowerShell,
**no Docker daemon, no Helm, no PostgreSQL, no GitHub remote**. Date: 2026-11-26.
Command: `python tools/nx.py check` → `passed=34 failed=0 skipped=3`.
This file lists only what was actually executed; it must be updated with every milestone.

## 1. Executed locally (results observed)

| Check | Command | Result |
|---|---|---|
| Python lint | `nx lint` (ruff check + format --check) | pass |
| Web lint | eslint `--max-warnings 0`, prettier `--check` | pass |
| Python types | `nx typecheck` (mypy `--strict`, 90 source files) | pass |
| Web types | `tsc --noEmit` | pass |
| Python unit tests | `pytest -m "not contract and not integration"` | **150 passed** |
| Python contract tests | `pytest -m contract` | **56 passed** (OpenAPI snapshot, SDK↔API, adapter ports ×10, module ports ×12) |
| Python coverage gate | `coverage report` over unit+contract, `fail_under=85` | **98%** (1745 statements, 22 missed) |
| Web tests | vitest | **37 passed** (3 files); lines 98.64%, statements 98.35%, branches 90.08% (thresholds 80/80/70) |
| Generated web types in sync | `npm run gen:api:check` | pass (also verified to fail when the file is tampered with) |
| Architecture boundaries | `lint-imports` | 4 contracts kept, 0 broken |
| Repo policy | `check:repo-policy` | pass (SHA-pinned actions, workflow permissions, ADR index, lock hashes, no secrets/workstation paths/localhost in source, contract doc per engine) |
| Deploy static policy | `check:deploy` | pass (no floating tags, no literal secrets, hardening/resources/probes on workloads) |
| Docker Compose config | `docker compose config -q` (release + dev override; no daemon needed) | pass; also fails correctly when required secrets are unset |
| Kustomize | `kubectl kustomize` base, staging, production, then hardening policy on the rendered output | pass |
| YAML | `yamllint --strict` | pass |
| GitHub workflows | `actionlint` incl. shellcheck on every `run:` block (shellcheck-py from the pinned lock) | pass (shellcheck findings in `release.yml` fixed) |
| Build | `python -m build --wheel` ×4; `vite build` | pass (4 wheels; JS 312 kB / 97 kB gzip) |
| Python SAST | `bandit` (shipped code; dev tooling with documented skips) | pass |
| Python dependency audit | `pip-audit` on `requirements/prod.txt` | no known vulnerabilities |
| npm dependency audit | `npm audit --omit=dev --audit-level=high` | 0 vulnerabilities |
| Secret scan | `detect-secrets-hook` vs `.secrets.baseline` (25 findings reviewed line by line, all false positives: names/placeholders/test fixtures) | pass |
| CI semantics | `CI=true` run of `test-integration` and `validate` | missing PostgreSQL/Helm correctly **fail** (not skip) |
| Live service | real `uvicorn` + `python -m nexora_control_plane.migrate` on SQLite, then `tests/smoke/smoke.py` | **5/5 smoke checks passed** |
| Task runner and checks | `ruff`, `mypy --strict`; `tools/tests`: runner policy (missing tool = SKIP locally / FAIL in CI, scoping, exit codes), repo policy, deploy checks, smoke script | pass (68 tests) |
| Setup from scratch | `python tools/nx.py setup` (venv from hash-pinned lock, `npm ci`) | pass |
| Release steps that need no Docker | `cyclonedx-py requirements`, `npm sbom`, placeholder substitution + `deploy.py --require-substituted` on a scratch copy (and the negative case on the unsubstituted overlay) | pass (output discarded; steps themselves proven runnable) |
| SSRF regression | tests: `probe_path` cannot change the probed host, credentials in `endpoint` rejected | pass |

## 2. Written but verified only in CI (not executed anywhere yet)

| Item | Where it will run | Why not local |
|---|---|---|
| PostgreSQL migrations + API (`test_migrate_then_serve_on_postgres`) | `integration.yml` (service container) | no PostgreSQL here; test is **skipped** locally (1 skipped) |
| `helm lint` / `helm template` incl. "rejects missing image tag" checks | `validate.yml` | Helm not installed locally |
| `docker build` of both images, Trivy image + config scan, SPDX SBOM | `images.yml` | Docker daemon not running |
| nginx configuration syntax (`nginx -t`) and CSP behaviour in a browser | first image/compose run | needs the image |
| Installing the lock file on Linux (`pip install --require-hashes`) | every Python CI job | lock resolved on Windows |
| CodeQL | `security.yml` (public repos / GHAS) | GitHub-hosted |
| Release: SHA-tagged image push, digest recording, SBOMs, chart package, manifest rendering, GitHub Release | `release.yml` on a `vX.Y.Z` tag | needs repository, registry, tag |
| Deploy to a server (SSH, compose pull/up, remote smoke) | `deploy.yml` (manual, approval-gated) | needs a server and GitHub environments |
| Dependabot, branch protection, secret scanning/push protection | GitHub settings | no repository yet |

## 3. Never executed / not implemented

- Any adapter against a **live engine** (Kafka, Kafka Connect, Flink, Spark, Iceberg REST, S3/MinIO, Trino,
  Airflow, Marquez, Prometheus). Probe paths/response shapes are from upstream documentation, unconfirmed.
- Any data path: ingestion, CDC, streaming/batch jobs, Iceberg tables, queries, lineage emission.
- Backup and restore (`docs/operations/backup-restore.md` is a procedure with a drill checklist, **not drilled**).
- Upgrade and rollback rehearsal; Kubernetes deployment on a real cluster; ExternalSecret reconciliation.
- Load, failure-injection, security penetration testing; browser/e2e tests of the UI against the real API
  (web tests mock `fetch`; API compatibility is covered by generated types and the OpenAPI contract).
- OIDC/RBAC (not implemented).
