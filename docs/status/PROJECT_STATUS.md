# Project status

_Milestone M0 (foundation). Last updated: 2026-11-26. Evidence for every "done" below is in
[TEST_EVIDENCE.md](TEST_EVIDENCE.md); anything not listed there as executed is not claimed._

## Summary

| Area | State | Notes |
|---|---|---|
| Repository, conventions, ADRs | **done** | 10 ADRs (8 accepted, 2 proposed), conventions, CONTRIBUTING, SECURITY |
| Control Plane API | **done (M0 scope)** | health/readiness/metrics, platform info, module + adapter catalog, connection registry, live health probes, audit log |
| Persistence and migrations | **done (M0 scope)** | PostgreSQL via SQLAlchemy/Alembic; models↔migration drift test; tested on SQLite locally, PostgreSQL only in CI |
| Domain modules (12) | **contracts only** | ports + in-memory fakes + contract tests; no module is backed by a real engine |
| Engine adapters (10) | **probe only** | health probes verified against mocked protocols; none verified against a live engine |
| Python SDK | **done (M0 scope)** | typed async client, contract-tested against the real app and the OpenAPI snapshot |
| Web UI | **done (M0 scope)** | overview, modules, adapters, connections, audit; token screen |
| Quality gates | **done** | `lint`, `typecheck`, `test`, `test-unit`, `test-contract`, `validate`, `build`, `security-check` execute real tools |
| CI/CD workflows | **written, not yet run** | actionlint clean; never executed on GitHub (no remote yet) |
| Deployment assets | **written, partly validated** | compose + kustomize render and pass policy checks locally; Helm, images, real server **not yet validated** |
| Authentication | **minimal** | one shared bearer token; OIDC/RBAC planned (ADR-0006) |

## Domain module maturity

| Module | Maturity | Criteria met | unmet | planned | Engines it is meant for |
|---|---|---|---|---|---|
| `ingestion` | contract | 2 | 0 | 1 | spark, airflow |
| `cdc` | contract | 2 | 0 | 1 | kafka-connect, kafka |
| `streaming` | contract | 2 | 0 | 1 | kafka |
| `processing` | contract | 2 | 0 | 1 | flink, spark |
| `lakehouse` | contract | 2 | 0 | 1 | iceberg-rest-catalog, object-store-s3 |
| `query` | contract | 2 | 0 | 1 | trino |
| `orchestration` | contract | 2 | 0 | 1 | airflow |
| `governance` | contract | 2 | 0 | 1 | — |
| `quality` | functional* | 2 | 0 | 1 | — |
| `lineage` | contract | 2 | 0 | 1 | openlineage |
| `observability` | contract | 2 | 0 | 1 | prometheus |
| `ai` | contract | 2 | 0 | 1 | — |

\* `quality` is functional because its rule evaluator (not_null, unique, range, regex, accepted_values) is
real, fully unit-tested logic that needs no external engine. It is not yet wired to any dataset source.
Every module has one `planned` criterion: verification against the real engine in CI.

Source of truth: each module's `module.toml`, served live by `GET /api/v1/modules`.

## Engine adapter maturity

All ten adapters (Kafka, Kafka Connect, Flink, Spark, Iceberg REST catalog, S3 object store, Trino, Airflow,
OpenLineage backend, Prometheus) are **`probe`**. Kafka is the weakest: TCP reachability only. The probe
paths and response shapes come from upstream documentation as known to the author and have **not** been
confirmed against live engines. See [`contracts/adapters/`](../../contracts/adapters).

## What does NOT exist yet (do not assume it works)

- Any data movement or transformation: ingestion, CDC pipelines, Flink/Spark jobs, Iceberg tables, Trino queries.
- Orchestration of real workflows, real lineage emission, scheduled quality runs, governance enforcement.
- Observability stack (dashboards, alert rules) and AI extensions beyond port definitions.
- OIDC/RBAC, multi-tenancy, rate limiting.
- A deployed environment: no server, registry or CI run exists yet.

## Risks and caveats

1. **Lock file portability.** `requirements/*.txt` were resolved on Windows. Packages with Linux-only
   dependencies would be missing; CI installs on Linux and will show it.
2. **Image digests** are resolved at release time, not committed. Base-image tags (`python:3.11.18-slim-bookworm`,
   `postgres:16.16-bookworm`) were the newest patch releases listed on Docker Hub on 2026-11-26; Trivy may still
   report fixable vulnerabilities in CI, which blocks publishing until the tags are bumped.
3. **Helm chart** was never rendered by Helm (not installed locally); CI runs `helm lint` and `helm template`.
4. **TypeScript 5.9** instead of 7.x until `typescript-eslint` and `openapi-typescript` support newer majors.
5. **GitHub actions** are pinned to SHAs resolved with `git ls-remote` on 2026-11-26; review them before first
   use (supply-chain hygiene) and let Dependabot maintain them.
6. **`CODEOWNERS`** has no owners until real handles are added; `SECURITY.md` has a TODO for a contact.

## Next

Push to GitHub and make the PR workflows green (M0.5), then follow [roadmap.md](../roadmap.md).
