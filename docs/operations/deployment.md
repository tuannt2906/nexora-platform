# Server deployment architecture

NEXORA is developed on a workstation and **never** built or run for production from it. The only
path to production is:

```
workstation -> git push -> GitHub Actions (verify, build, scan, SBOM)
            -> container registry (immutable tag = git SHA)
            -> production server pulls that tag (compose) or the cluster pulls it (Kubernetes/Helm)
```

Servers never receive source code, never build images, and never run `latest`.

## What is deployed in this milestone

| Component | Image | Port | State |
|-----------|-------|------|-------|
| `web` (static React bundle, nginx-unprivileged) | `<registry>/web:<sha>` | 8080 | stateless |
| `control-plane` (FastAPI, uvicorn) | `<registry>/control-plane:<sha>` | 8000 | stateless |
| `migrate` (one-shot: `python -m nexora_control_plane.migrate`) | same image as `control-plane` | - | runs to completion |
| PostgreSQL 16 | `postgres:16.16-bookworm` (compose) or managed service | 5432 | **the only datastore** |

The data engines (Kafka, Flink, Spark, Iceberg catalog, Trino, ...) are **not** deployed by these
assets. The Control Plane only holds *connections* to engines that you operate separately and
probes their health through adapters. See `docs/status/` for the honest per-engine maturity.

```
            Internet
               |
        [ TLS terminator / Ingress ]
               |  :8080
            +-----+   /api/*    +---------------+        +------------+
            | web | ----------> | control-plane | -----> | PostgreSQL |
            +-----+             +---------------+        +------------+
                                       |  HTTP(S) health probes
                                       v
                           external engines (Trino, Flink, ...)
```

## Choosing a target

| | Docker Compose (`deploy/compose`) | Kubernetes (`deploy/kubernetes`, `deploy/helm/nexora`) |
|--|--|--|
| Fits | one server, staging, small production | production with HA, rolling updates, policy |
| Database | Postgres container + named volume (you own backups) | external/managed Postgres (secret `database-url`) |
| Secrets | `.env` file, mode 0600, outside git | External Secrets Operator -> Secret |
| Migrations | `migrate` service, `service_completed_successfully` gate | Job (kustomize) or pre-upgrade hook (Helm) |
| HA | no | replicas, PDB, HPA, anti-affinity via topology spread |
| Network isolation | `backend` network is `internal: true`; only web publishes a port | default-deny NetworkPolicies |

Kustomize and Helm are two renderings of the same design. Pick **one** per environment; do not
mix them for the same namespace.

## Docker Compose: first deployment

Prerequisites: Docker Engine with the compose plugin, access to the registry, a TLS-terminating
reverse proxy in front of port 8080 (Caddy, nginx, a cloud load balancer, ...).

```bash
git clone <repo> && cd nexora-platform/deploy/compose
cp .env.example .env && chmod 600 .env       # fill in every CHANGE_ME
docker login ghcr.io                          # read-only registry token
docker compose --env-file .env config -q      # fails loudly if a required variable is missing
docker compose --env-file .env pull
docker compose --env-file .env up -d
NEXORA_API_TOKEN=... python ../../tests/smoke/smoke.py --base-url http://127.0.0.1:8080 \
  --token-env NEXORA_API_TOKEN --wait-seconds 90
```

`NEXORA_IMAGE_TAG` must be the full git SHA of a release that CI published and scanned. The
compose file refuses to start without it (`${NEXORA_IMAGE_TAG:?...}`).

## Kubernetes (kustomize): first deployment

1. Cluster add-ons: ingress-nginx, cert-manager (or your TLS secret `nexora-tls`), External
   Secrets Operator, a `ClusterSecretStore` named `nexora-secret-store` (see `secrets.md`).
2. The release workflow renders `deploy/kubernetes/overlays/<env>` with the owner and image tag
   substituted (see `deploy/kubernetes/README.md`). The substituted output is what you apply.
3. Apply following the procedure in `upgrade-rollback.md` (migration Job first, then rollout).

## Kubernetes (Helm): first deployment

```bash
helm upgrade --install nexora deploy/helm/nexora -n nexora --create-namespace \
  --set image.registry=ghcr.io/<owner>/nexora-platform --set image.tag=<git-sha> \
  --set ingress.enabled=true --set ingress.host=nexora.example.com \
  --set secrets.externalSecret.enabled=true --atomic --timeout 10m
```

On the very first install the Secret `nexora-secrets` must already exist because the migration
hook runs before other resources: apply the ExternalSecret first
(`helm template ... -s templates/externalsecret.yaml | kubectl apply -f -`) and wait until
`kubectl -n nexora get secret nexora-secrets` succeeds.

## Health checks

| Endpoint | Meaning | Used by |
|----------|---------|---------|
| `GET /healthz` | process is alive, no dependencies | container HEALTHCHECK, k8s liveness/startup |
| `GET /readyz` | database reachable; 503 otherwise | compose healthcheck, k8s readiness |
| `GET /metrics` | Prometheus exposition | Prometheus / ServiceMonitor |

A started container is **not** evidence of readiness. Always run the smoke test
(`runbook-smoke.md`) after a deployment, and treat it as necessary but not sufficient.

## Not covered yet (tracked in the roadmap)

* TLS termination and certificate management for the compose path (bring your own proxy).
* Multi-node Postgres HA, point-in-time recovery (WAL archiving). Current backup is logical dumps.
* Deployment of the data engines themselves.
