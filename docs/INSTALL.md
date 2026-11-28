# Installation guide

Three audiences, three sections: [developer workstation](#1-developer-workstation),
[server with Docker Compose](#2-server-docker-compose) and [Kubernetes](#3-kubernetes). A Vietnamese
version is in [INSTALL.vi.md](INSTALL.vi.md).

> **Scope reminder.** NEXORA M0 installs the control plane (API, web console, PostgreSQL). It does **not**
> install Kafka, Flink, Spark, Trino, Iceberg or any other data engine: those run on their own infrastructure and
> are registered in NEXORA as connections. See [PROJECT_STATUS](status/PROJECT_STATUS.md).

## 1. Developer workstation

Requirements: Git, **Python 3.11**, **Node.js ≥ 22** (with npm). Docker and Kubernetes are **not** needed.

```bash
git clone https://github.com/tuannt2906/nexora-platform.git
cd nexora-platform
python tools/nx.py setup      # .venv from the hash-pinned lock + workspace packages + npm ci (apps/web)
python tools/nx.py check      # lint, typecheck, tests, validate, build, security checks
```

On Linux/macOS/CI `make setup` and `make check` are equivalent (`make` is optional). Windows PowerShell and
Linux/macOS use the same `python tools/nx.py <target>` commands. Targets: `lint typecheck test test-unit
test-contract test-integration validate build docker-build security-check openapi-update`.

Optional local tools (CI always runs the corresponding checks): `helm` (chart lint/template), Docker (image
builds), PostgreSQL (`make test-integration`, set `NEXORA_TEST_DATABASE_URL`). When a tool is missing the runner
prints a loud **SKIP**, and with `CI=true` it fails.

### Run the API and the UI locally (light, SQLite)

```bash
# Linux / macOS (Git Bash)
export NEXORA_DATABASE_URL='sqlite+pysqlite:////tmp/nexora-dev.db'      # development only
export NEXORA_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "token: $NEXORA_API_TOKEN"
.venv/bin/python -m nexora_control_plane.migrate
.venv/bin/python -m uvicorn nexora_control_plane.main:app --reload     # http://127.0.0.1:8000/docs
# second terminal
cd apps/web && VITE_DEV_API_TARGET=http://127.0.0.1:8000 npm run dev
```

```powershell
# Windows PowerShell
$env:NEXORA_DATABASE_URL = "sqlite+pysqlite:///$env:TEMP/nexora-dev.db".Replace('\','/')
$env:NEXORA_API_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python -m nexora_control_plane.migrate
.\.venv\Scripts\python -m uvicorn nexora_control_plane.main:app --reload
# second terminal: cd apps\web; $env:VITE_DEV_API_TARGET="http://127.0.0.1:8000"; npm run dev
```

Open the web URL printed by Vite and paste the token on the token screen.

## 2. Server (Docker Compose)

Single-node deployment: PostgreSQL + one-shot migration + control plane + web (nginx). Images are pulled by an
**immutable tag (the full git SHA of a release)**; the repository checkout only provides the compose files.

### Server prerequisites

- Linux x86-64 with **Docker Engine ≥ 24** and the **Compose v2 plugin** (`docker compose version`), `git`,
  `openssl`, `python3` (for the smoke test), outbound HTTPS to `ghcr.io`.
- A firewall that exposes only 80/443 (see TLS below). The web container publishes port **8080** on all
  interfaces by default; do not expose it directly to the internet without TLS.

### 2.1 Get the code at a released commit

```bash
sudo git clone https://github.com/tuannt2906/nexora-platform.git /opt/nexora
cd /opt/nexora
git fetch --tags
git checkout --detach v0.1.0                 # a release tag created by the maintainer
RELEASE_SHA=$(git rev-parse HEAD)            # this exact SHA is the image tag
echo "$RELEASE_SHA"
```

### 2.2 Create the secrets/env file outside the repository

```bash
sudo install -d -m 750 /etc/nexora
sudo cp deploy/compose/.env.example /etc/nexora/nexora.env
sudo chmod 600 /etc/nexora/nexora.env
sudo $EDITOR /etc/nexora/nexora.env
```

Set: `NEXORA_IMAGE_REGISTRY=ghcr.io/tuannt2906/nexora-platform`, `NEXORA_IMAGE_TAG=<RELEASE_SHA>`,
`NEXORA_POSTGRES_PASSWORD=$(openssl rand -hex 24)`, `NEXORA_API_TOKEN=$(openssl rand -hex 32)`. Use only
`[A-Za-z0-9_-]` in the password (it is embedded in a URL). Optional: `NEXORA_WEB_PORT`, `NEXORA_LOG_LEVEL`,
`NEXORA_CORS_ORIGINS`. Never commit this file; it is the only place production secrets live.

### 2.3 Make the images pullable

GitHub Container Registry packages are **private by default**, even for a public repository. After the first
release publishes them, either set both packages (`nexora-platform/control-plane`, `nexora-platform/web`) to
*Public* (GitHub → profile → Packages → package → Package settings → Change visibility), or log in on the server:

```bash
echo "$GHCR_READ_TOKEN" | docker login ghcr.io -u tuannt2906 --password-stdin   # PAT with read:packages
```

### 2.4 Start

```bash
cd /opt/nexora/deploy/compose
docker compose --env-file /etc/nexora/nexora.env pull
docker compose --env-file /etc/nexora/nexora.env up -d --wait
docker compose --env-file /etc/nexora/nexora.env ps
```

`up --wait` returns when PostgreSQL, the migration and the services are healthy (the migration must have
completed successfully before the API starts).

### 2.5 Verify

```bash
cd /opt/nexora
set -a; . /etc/nexora/nexora.env; set +a
python3 tests/smoke/smoke.py --base-url "http://127.0.0.1:${NEXORA_WEB_PORT:-8080}" --token-env NEXORA_API_TOKEN
```

Expect `4/4 smoke checks passed` (the metrics check is reported as SKIP because `/metrics` is not exposed through the web tier). Then open `http://<server>:8080` (or your TLS URL) and paste `NEXORA_API_TOKEN`.

### 2.6 TLS and exposure

Terminate TLS in front of the web container with a reverse proxy of your choice (Caddy, nginx, Traefik) proxying
to `127.0.0.1:8080`, and firewall port 8080. `/metrics` is unauthenticated: do not route it publicly.

### 2.7 Upgrade and roll back

```bash
cd /opt/nexora && git fetch --tags && git checkout --detach v0.2.0
sudo sed -i "s/^NEXORA_IMAGE_TAG=.*/NEXORA_IMAGE_TAG=$(git rev-parse HEAD)/" /etc/nexora/nexora.env
cd deploy/compose
docker compose --env-file /etc/nexora/nexora.env pull
docker compose --env-file /etc/nexora/nexora.env up -d --wait
```

Roll back by checking out the previous tag and setting the previous SHA. Migrations are expand-only, so the
previous application version runs against the new schema ([ADR-0010](adr/0010-database-migrations.md)). Back up
before upgrading: [backup-restore.md](operations/backup-restore.md); details: [upgrade-rollback.md](operations/upgrade-rollback.md).
The `deploy.yml` workflow automates 2.1–2.5 over SSH with approval.

### 2.8 Bootstrap without a release (evaluation only)

Before the first release exists there are no images to pull. For a trial on a server you control you can build
from source (not for production, because it deploys unverified source):

```bash
cd /opt/nexora/deploy/compose
# in the env file: NEXORA_IMAGE_REGISTRY=nexora-local  NEXORA_IMAGE_TAG=bootstrap  + the two secrets
docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file /etc/nexora/nexora.env up -d --build --wait
```

## 3. Kubernetes

Plain manifests (kustomize) and a Helm chart, both expecting an external or managed PostgreSQL 16 and secrets
from an external secret manager (External Secrets Operator). Prerequisites: cluster ≥ 1.27, an ingress controller
(`ingress-nginx` is assumed by the NetworkPolicy), External Secrets Operator with a `ClusterSecretStore` named
`nexora-secret-store` (or change the name in the ExternalSecret / Helm values) holding the database URL and API token.

- kustomize: [`deploy/kubernetes/README.md`](../deploy/kubernetes/README.md) — render with the release tag
  (`REPLACE_WITH_RELEASE_SHA` / `REPLACE_WITH_OWNER` are substituted by the release workflow; the release
  attaches ready-to-apply `k8s-staging.yaml` / `k8s-production.yaml`).
- Helm: `helm upgrade --install nexora deploy/helm/nexora -n nexora --create-namespace
  --set image.registry=ghcr.io/tuannt2906/nexora-platform --set image.tag=<RELEASE_SHA>`
  (the chart refuses to render without an image tag or with `latest`; secrets come from the ExternalSecret).

Neither path has been exercised on a real cluster yet; see [TEST_EVIDENCE](status/TEST_EVIDENCE.md).

## 4. Maintainer: first release

1. CI green on `main` (all workflows under *Actions*).
2. `git tag v0.1.0 && git push origin v0.1.0` → `release.yml` re-runs every gate, publishes SHA-tagged images,
   SBOMs, wheels, web bundle, Helm chart and rendered manifests to a GitHub Release.
3. Set the two GHCR packages to Public (or use a read token on servers), then follow section 2.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `set NEXORA_IMAGE_TAG to an immutable release tag` | env file not passed (`--env-file`) or variable empty |
| `pull access denied` / `unauthorized` for ghcr.io | package still private: make it public or `docker login ghcr.io` |
| `migrate` exits non-zero, API never starts | wrong `NEXORA_POSTGRES_PASSWORD` (also after changing it on an existing volume) or unreachable DB: `docker compose logs migrate postgres` |
| API container restarts: `NEXORA_API_TOKEN ... at least 24 characters` | token too short |
| UI shows 401 after login | pasted token differs from `NEXORA_API_TOKEN` in the running container (recreate after editing the env file: `up -d`) |
| `/docs` returns 404 | expected when `NEXORA_ENVIRONMENT=production` |
