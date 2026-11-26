# Secrets management

**Rule: production secrets never enter this repository** (not in code, compose files, manifests,
Helm values, CI logs or issue trackers). The repo only contains *references* to secrets and
`CHANGE_ME` placeholders. `make validate` and `make security-check` fail on literal secrets.

## Inventory

| Secret | Consumer | Format | Where it lives |
|--------|----------|--------|----------------|
| `NEXORA_DATABASE_URL` | control-plane, migrate | `postgresql+psycopg://user:pass@host:5432/db` | secret manager -> Secret `nexora-secrets` |
| `NEXORA_API_TOKEN` | control-plane (bearer for `/api/v1/*`), smoke test | random 32+ bytes | secret manager |
| `NEXORA_POSTGRES_PASSWORD` | compose Postgres + app | `[A-Za-z0-9_-]` only (embedded in a URL) | `.env` on the server |
| registry pull credentials | servers / cluster | token with `read:packages` only | docker login / `imagePullSecrets` |

Engine credentials are not stored by the Control Plane: a connection stores only a `secret_ref`
pointer that a runtime resolver turns into a value.

## Kubernetes: External Secrets Operator

1. Install ESO (https://external-secrets.io) and create a `ClusterSecretStore` named
   `nexora-secret-store` for your backend (Vault, AWS Secrets Manager, GCP Secret Manager, Azure
   Key Vault, ...). Authenticate it with workload identity / IRSA where possible, not static keys.
2. Create these entries in the manager: `nexora/<env>/database-url` and `nexora/<env>/api-token`
   (the paths are in `deploy/kubernetes/base/externalsecret.yaml`, patched per overlay).
3. ESO materialises Secret `nexora-secrets` (refresh every hour); pods read it via `envFrom`.
4. Restrict RBAC: only ESO and the operators of the namespace can read Secrets; the
   application ServiceAccount has no token mounted.

## Docker Compose servers

* `.env` lives only on the server, owner root, mode `0600`, never in git (`.gitignore` blocks
  `.env`).
* Prefer generating it from your secret manager at deploy time over typing values by hand.
* Generate values with `openssl rand -hex 24` (password) and `openssl rand -hex 32` (token).

## CI / GitHub

* The release pipeline authenticates to the registry with the workflow `GITHUB_TOKEN`; no
  long-lived registry secret is stored.
* Deployment credentials (kubeconfig/OIDC role, SSH key) are stored as **GitHub Environment**
  secrets for `staging` / `production`, with required reviewers on `production`.
* Secret scanning runs on every pull request. A finding blocks the merge.

## Rotation

| Secret | Procedure | Impact |
|--------|-----------|--------|
| `NEXORA_API_TOKEN` | write a new value in the manager, wait for ESO refresh (or force-sync), `rollout restart` the control plane, update clients/smoke test | the milestone-1 API accepts one token: clients get `401` between restart and update. Multi-token overlap is a roadmap item |
| Database password | create the new credential (or `ALTER ROLE ... PASSWORD`), update `database-url`, force-sync, `rollout restart`; compose: edit `.env`, change the role password, `up -d` | brief connection errors during restart |
| Registry token | issue new read-only token, update servers/`imagePullSecrets`, revoke old | none if done in this order |

Rotate **immediately** after any suspected exposure, then follow with: revoke the old value,
search logs for use of it, document the incident.

## If a secret is committed by mistake

1. Treat it as compromised: rotate it first (table above). Rewriting git history does not
   un-leak a secret that was pushed.
2. Remove it from the repository and history (`git filter-repo`), force-push only with the
   team's agreement, and invalidate caches/forks where possible.
3. Add or improve the scanning rule that should have caught it.
