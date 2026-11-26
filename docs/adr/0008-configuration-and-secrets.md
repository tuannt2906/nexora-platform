# 0008. Configuration from environment; secrets outside the repository

Status: Accepted
Date: 2026-11-26

## Decision

- Services are configured only through `NEXORA_*` environment variables (pydantic-settings). There are no
  config files with environment-specific values in the repository and no hardcoded hosts or paths.
- Secrets (`NEXORA_DATABASE_URL`, `NEXORA_API_TOKEN`) have **no defaults**: a missing secret stops startup.
  They are typed `SecretStr` and never logged or serialised.
- The repository contains templates only (`deploy/compose/.env.example`, Helm values without secrets,
  an `ExternalSecret` manifest). Real values live in an external secret manager (External Secrets Operator
  on Kubernetes; a root-owned env file on single-node compose servers) — see `docs/operations/secrets.md`.
- Engine credentials are never stored by the control plane: a connection stores a `secret_ref` pointer.
- `.gitignore` blocks `.env*` (except `*.example`), keys and secret manifests; `make validate` and
  `detect-secrets` fail the build if one slips in.

## Consequences

Rotation is an operation on the secret manager plus a rollout, not a code change. Local development needs
the two secrets exported in the shell; `deploy/compose/.env.example` documents them.
