# 0002. Technology baseline

Status: Accepted
Date: 2026-11-26

## Context

The platform is developed on an ordinary Windows workstation and deployed to Linux servers. The control
plane orchestrates heavy engines; it must not itself be heavy. Contributors need a fast inner loop.

## Decision

- **Control Plane:** Python 3.11, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL 16, structured JSON logging
  (structlog), Prometheus metrics. Python was chosen because the data ecosystem (Spark, Trino, Iceberg
  tooling, orchestration) is Python-first, so SDKs and adapters share a language with their users.
- **Frontend:** React + TypeScript (strict) + Vite, TanStack Query, plain CSS. API types are generated from
  the OpenAPI contract; a CI check fails on drift.
- **Packaging:** hatchling per distribution; installs from hash-pinned lock files (ADR-0007).
- **Containers:** multi-stage, non-root, read-only-root-filesystem compatible images.
- **Database portability:** models use portable SQLAlchemy types so unit tests run on SQLite while
  integration tests and production use PostgreSQL.

## Consequences

Python 3.11 is the lock-file target; moving to a newer minor version means re-locking and re-running CI.
The frontend is on TypeScript 5.9 because the current `typescript-eslint` and `openapi-typescript` releases
do not yet support newer major versions (recorded in `apps/web/README.md`).
