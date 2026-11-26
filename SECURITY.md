# Security policy

## Reporting a vulnerability

Do not open a public issue. Use GitHub private vulnerability reporting:
**Security → Report a vulnerability** on <https://github.com/tuannt2906/nexora-platform>.
Include the affected version/commit, impact and a minimal reproduction. You will get an acknowledgement
as soon as the maintainer can; there is no formal SLA for this project yet.

Only the latest release and `main` receive security fixes.

## Scope and current posture (M0)

- Authentication is a single shared bearer token ([ADR-0006](docs/adr/0006-authentication-and-authorization.md));
  run behind TLS on a private network until OIDC/RBAC lands.
- Connection endpoints are validated against SSRF-sensitive targets (non-HTTP schemes, link-local/metadata
  addresses, credentials in the URL, `probe_path` values that could change the host); private addresses are
  allowed because engines live there.
- `/metrics` is unauthenticated: restrict it at the network layer (the Kubernetes NetworkPolicy only admits the
  web tier and the monitoring namespace).
- Secrets are never stored in the repository or the database (only `secret_ref` pointers).

## Repository settings (recommended for the maintainer)

Branch protection on `main` (required status checks from the PR workflows, no force pushes), secret scanning
with push protection, Dependabot alerts and security updates, private vulnerability reporting, and environment
protection rules (required reviewers) for `staging` and `production`.
