# NEXORA Platform

[![Backend CI](https://github.com/tuannt2906/nexora-platform/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/tuannt2906/nexora-platform/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/tuannt2906/nexora-platform/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/tuannt2906/nexora-platform/actions/workflows/frontend-ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Control plane for an enterprise lakehouse data platform (ingestion, CDC, streaming, processing, Iceberg,
query, orchestration, governance, quality, lineage, observability, AI extensions).

> **Honest status:** this repository is the validated *foundation* (milestone M0). The control plane, module
> contracts, engine health probes, SDK, UI, CI/CD and deployment assets are implemented and tested. **No data
> engine is driven functionally yet** — adapters are health probes verified against mocked protocols.
> Details: [PROJECT_STATUS](docs/status/PROJECT_STATUS.md) · [TEST_EVIDENCE](docs/status/TEST_EVIDENCE.md) ·
> [roadmap](docs/roadmap.md).

## How development works

```
workstation ──push──► GitHub ──► CI (PR gates) ──merge/tag──► release ──► container registry ──► server
```

The workstation never runs the data platform. It runs editors, tests, linters, type checkers and static
validation. See [ADR-0003](docs/adr/0003-development-to-production-model.md).

## Repository map

| Path | Content |
|---|---|
| `packages/nexora-core` | kernel: settings, logging, errors, engine-adapter contract |
| `packages/nexora-modules` | 12 domain modules (ports, fakes, `module.toml`) and engine adapters |
| `services/control-plane` | FastAPI service, PostgreSQL persistence, Alembic migrations |
| `sdk/python` | typed async client |
| `apps/web` | React + TypeScript UI |
| `contracts/` | OpenAPI snapshot, adapter contract documents |
| `infra/docker` | Dockerfiles, nginx config |
| `deploy/` | Docker Compose, Kubernetes (kustomize), Helm chart |
| `tools/` | task runner (`nx.py`), policy/deploy checks |
| `tests/smoke` | post-deployment smoke test |
| `docs/` | architecture, ADRs, engineering conventions, operations runbooks, status |

## Workstation setup (Windows/macOS/Linux)

Requirements: Git, Python 3.11, Node.js ≥ 22. Nothing else — no Docker, no Kubernetes.

```bash
python tools/nx.py setup        # creates .venv from the hash-pinned lock, npm ci for the web app
python tools/nx.py check        # everything a pull request must pass
```

`make <target>` does the same where `make` exists (CI, Linux servers); on Windows use `python tools/nx.py <target>`.

| Target | What it executes |
|---|---|
| `lint` | ruff check + format check; eslint + prettier |
| `typecheck` | mypy `--strict`; `tsc --noEmit` |
| `test-unit` | pytest (coverage gate) ; vitest (coverage gate) |
| `test-contract` | OpenAPI snapshot, SDK ↔ API, adapter port contracts; generated web types in sync |
| `test` | unit + contract |
| `test-integration` | tests needing PostgreSQL (`NEXORA_TEST_DATABASE_URL`); loud SKIP locally, failure in CI |
| `validate` | architecture boundaries (import-linter), repo policy, YAML, workflows (actionlint), compose / kustomize / Helm validation |
| `build` | Python wheels, web bundle |
| `docker-build` | container images (needs a Docker daemon; always run in CI) |
| `security-check` | bandit, pip-audit, npm audit, detect-secrets |

A tool that is not installed is reported as **SKIP (NOT verified)** locally and as a **failure** in CI.
Extra optional local tools: `helm` (chart lint/template), Docker (image builds). Both run in CI regardless.

## Install

Step-by-step guides (developer workstation, server with Docker Compose, Kubernetes, upgrade/rollback,
troubleshooting): **[docs/INSTALL.md](docs/INSTALL.md)** · tiếng Việt: [docs/INSTALL.vi.md](docs/INSTALL.vi.md).

## Deploying

Never from source. See [docs/architecture/server-deployment.md](docs/architecture/server-deployment.md) and the
[operations runbooks](docs/operations/deployment.md): tag a release → CI builds immutable images → deploy the
published tag (compose, kustomize or Helm). Production secrets stay on the server / in the secret manager.

## Contributing and security

[CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [conventions](docs/engineering/conventions.md)

## License

Copyright 2026 tuannt2906. Licensed under the [Apache License, Version 2.0](LICENSE); see [NOTICE](NOTICE).
Contributions are accepted under the same license (Apache-2.0, section 5).
