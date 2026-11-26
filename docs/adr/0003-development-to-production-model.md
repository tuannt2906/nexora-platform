# 0003. Workstation → Git → CI/CD → registry → server

Status: Accepted
Date: 2026-11-26

## Context

Development happens on a personal workstation. The Data Platform (Kafka, Flink, Spark, Iceberg, Trino ...)
runs on dedicated servers. The workstation has no production resources and must stay light.

## Decision

1. The workstation is **not** a runtime environment. It runs editors, Claude Code, unit/contract tests,
   linters, type checkers, configuration validation and (optionally) Docker image builds.
2. No local Kubernetes and no requirement to run the full platform. Docker Compose is never a prerequisite
   for a development task (`make lint`, `make test`, `make validate` need no Docker).
3. Every change reaches production only through: pull request → CI (validation) → merge to `main` →
   version tag → release workflow (re-runs all gates, builds, scans, publishes immutable images) →
   approved deployment of an already-published image tag.
4. Source code is never deployed. Servers pull **images** referenced by immutable tag (git SHA); the
   server's checkout of this repo supplies only deployment manifests at the same commit.
5. PR validation (`backend-ci`, `frontend-ci`, `validate`, `integration`, `security`, `images`) is separate
   from release (`release.yml`) and deployment (`deploy.yml`, manual and approval-gated).
6. Application code reads all environment-specific values from environment variables and contains no
   workstation paths or hardcoded development addresses (enforced by `make validate`).

## Consequences

A green workstation run predicts a green CI run because both execute the same task runner (ADR-0005).
Things that cannot be proven on the workstation (image builds, Helm rendering, integration with real
engines) are explicitly listed as CI-only in `docs/status/TEST_EVIDENCE.md`.
