# Test evidence

This file lists only what was actually executed; update it with every milestone.

- **Local run:** Windows 11 workstation, Python 3.11.9, Node 24, **no Docker daemon, no Helm, no PostgreSQL**.
  `python tools/nx.py check` → `passed=34 failed=0 skipped=3`.
- **CI run:** GitHub Actions on `main` at commit `96a4ba7` (2026-11-28), Ubuntu 24.04 runners. All seven
  pull-request workflows plus CodeQL were green. Run history: <https://github.com/tuannt2906/nexora-platform/actions>.
  CI needed four rounds of fixes before going green (Trivy findings, Helm error format, a smoke-test design
  flaw, the nginx base image); the fixes are in the commit history.

## 1. Executed locally (results observed)

| Check | Command | Result |
|---|---|---|
| Python lint | ruff check + format --check | pass |
| Web lint | eslint `--max-warnings 0`, prettier `--check` | pass |
| Python types | mypy `--strict` (91 source files) | pass |
| Web types | `tsc --noEmit` | pass |
| Python unit tests | `pytest -m "not contract and not integration"` | **152 passed** |
| Python contract tests | `pytest -m contract` | **56 passed** (OpenAPI snapshot, SDK↔API, adapter ports ×10, module ports ×12) |
| Python coverage gate | `coverage report` over unit+contract, `fail_under=85` | **98%** (1745 statements, 22 missed) |
| Web tests | vitest | **37 passed**; lines 98.64%, branches 90.08% (thresholds 80/70) |
| Generated web types in sync | `npm run gen:api:check` | pass |
| Architecture boundaries | `lint-imports` | 4 contracts kept, 0 broken |
| Repo policy | `check:repo-policy` | pass |
| Deploy static policy | `check:deploy` | pass |
| Docker Compose config | `docker compose config -q` (release + dev override) | pass; fails correctly when secrets are unset |
| Kustomize | `kubectl kustomize` base/staging/production + hardening policy | pass |
| YAML / workflows | `yamllint --strict`; `actionlint` with shellcheck | pass |
| Build | `python -m build --wheel` ×4; `vite build` | pass |
| Security | bandit, pip-audit (prod lock), npm audit (0), detect-secrets vs baseline | pass |
| CI strictness | `CI=true` with PostgreSQL/Helm absent | **fails** (never a silent skip) |
| Live service | `uvicorn` + migrate on SQLite, then `tests/smoke/smoke.py` | 4/4 checks passed (metrics reported as SKIP) |
| Release steps without Docker | `cyclonedx-py`, `npm sbom`, overlay substitution + `--require-substituted` | pass (scratch output) |

## 2. Executed in GitHub Actions (observed green on `96a4ba7`)

| Check | Workflow | What it proved |
|---|---|---|
| Lint, types, unit + contract tests, coverage gate, wheels | Backend CI | the pinned lock installs on **Linux** and everything passes there |
| Lint, types, tests, build | Frontend CI | `npm ci` from the lockfile; generated API types in sync |
| PostgreSQL migrations and API | Integration tests | Alembic migrations and the API against **real PostgreSQL 16** |
| `helm lint`, `helm template` (all optional features; missing tag and `latest` rejected), compose, kustomize | Validate configuration | the Helm chart renders with real Helm 3.22 |
| Image builds, Trivy vulnerability scan (fixable HIGH/CRITICAL fail), SPDX SBOM, Trivy IaC/Dockerfile scan | Container images | both images build and had no fixable HIGH/CRITICAL findings at scan time |
| Compose stack end-to-end | Stack smoke test | PostgreSQL → migration → API → nginx web tier started healthy; the smoke test passed through the web proxy; `/metrics` served by the API |
| bandit, pip-audit, npm audit, detect-secrets, CodeQL (Python, JS/TS) | Security | no findings |
| Dependabot (actions, npm, pip, docker, docker-compose) | Dependabot | configuration valid |

## 3. Written but never executed

| Item | Why |
|---|---|
| `release.yml` (tag → re-run gates → publish SHA-tagged images, SBOMs, chart, rendered manifests, GitHub Release) | runs only on a version tag |
| `deploy.yml` (SSH deployment with approval) | needs a server and GitHub environments |
| Image signing (cosign, opt-in) | needs `NEXORA_SIGN_IMAGES=true` |
| Kubernetes deployment, ExternalSecret reconciliation, Helm install on a real cluster | no cluster |
| Backup and restore (`docs/operations/backup-restore.md`), upgrade/rollback rehearsal | procedures exist, drill not performed |
| TLS reverse proxy, firewalling, `/metrics` network restriction on a real server | no server |

## 4. Not implemented / never exercised

- Any adapter against a **live engine** (Kafka, Kafka Connect, Flink, Spark, Iceberg REST, S3/MinIO, Trino,
  Airflow, Marquez, Prometheus). Probe paths and response shapes come from upstream documentation, unconfirmed.
- Any data path: ingestion, CDC, streaming/batch jobs, Iceberg tables, queries, lineage emission.
- Browser/e2e tests of the UI against the real API (web unit tests mock `fetch`; the full stack is only
  exercised by the HTTP smoke test).
- Load, failure-injection and penetration testing; OIDC/RBAC.
