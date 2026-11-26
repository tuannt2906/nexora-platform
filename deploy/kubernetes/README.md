# Kubernetes deployment (kustomize)

```
base/                 environment-neutral manifests (hardened, default-deny network)
overlays/staging/     staging: 1-2 replicas, staging secret paths and hostname
overlays/production/  production: 2-6 replicas
```

Render locally (no cluster needed): `kubectl kustomize deploy/kubernetes/overlays/production`.

## What is NOT in this repository

* **Secrets.** The `ExternalSecret` in `base/` only references keys in your external secret
  manager (Vault, AWS/GCP/Azure secret manager, ...). The real values live there. You must
  install External Secrets Operator and create a `ClusterSecretStore` named
  `nexora-secret-store` (or patch the name). See `docs/operations/secrets.md`.
* **PostgreSQL.** Production uses a managed or separately operated PostgreSQL 16; its URL is
  the `database-url` secret. The compose stack ships a Postgres container only for single-node
  hosts.
* **Cluster add-ons:** an NGINX ingress controller (`ingress-nginx` namespace), cert-manager
  for the `nexora-tls` secret, optional Prometheus (`monitoring` namespace).

## Release placeholders

Overlay `kustomization.yaml` files contain `REPLACE_WITH_OWNER` and `REPLACE_WITH_RELEASE_SHA`.
They are the only places these strings may appear. The release workflow substitutes them with
the registry owner and the immutable image tag, then verifies with
`python tools/checks/deploy.py --require-substituted deploy/kubernetes/overlays/<env>`.
Never hand-edit them to a mutable tag such as `latest`.

## Migrations

Migrations run as the Job `nexora-migrate` BEFORE the Deployments roll. Jobs are immutable, so
delete the previous one first. Full procedure: `docs/operations/upgrade-rollback.md`.
