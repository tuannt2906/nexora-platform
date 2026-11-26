# 0006. Authentication and authorization roadmap

Status: Proposed
Date: 2026-11-26

## Context

The first milestone needs the API protected, but there is no identity provider yet and no user model.

## Decision

- **Now (M0):** a single shared bearer token (`NEXORA_API_TOKEN`, minimum 24 characters, compared in
  constant time) protects every `/api/v1/*` endpoint. `/healthz`, `/readyz` and `/metrics` are open
  (metrics must be restricted at the network layer; see `deploy/kubernetes` NetworkPolicy). All mutations
  are written to the audit log with a coarse actor (`api-token`).
- **Planned (M1):** OIDC login for humans (authorization-code + PKCE in the SPA through the backend),
  short-lived service tokens for machines, and role-based access control with the governance module acting
  as the policy decision point (`PolicyDecisionPoint` port). The audit actor becomes the real subject.
- The single-token mode will be removed, not kept as a backdoor, once OIDC is in place.

## Consequences

M0 is suitable for a private network behind a TLS-terminating ingress, not for multi-tenant exposure. The
token must be rotated through the external secret manager (see `docs/operations/secrets.md`). The
decision stays `Proposed` until the OIDC provider is chosen.
