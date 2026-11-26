# Upgrade and rollback

Principles:

1. **Immutable tags.** An upgrade means pointing the deployment at a different git-SHA tag that
   CI built, scanned and published. Nothing is edited on the server; nothing is built on the
   server; `latest` is never used.
2. **Backup first.** Take and verify a backup (`backup-restore.md`) before any upgrade that
   contains a migration.
3. **Migrations before rollout.** The database is migrated by the one-shot migration step
   *before* new application pods/containers take traffic.
4. **Expand / contract.** Schema changes are shipped so that the previous release still works
   against the new schema (see below). This is what makes application rollback safe.

## Migration policy (expand / contract)

| Release | Allowed in the migration | Application behaviour |
|---------|--------------------------|----------------------|
| N (expand) | add tables, add **nullable** columns / columns with defaults, add indexes (`CONCURRENTLY` where large), add new constraints as `NOT VALID` then validate later | N writes both old and new shape if needed; N-1 keeps working |
| N+1 (contract) | drop columns/tables, tighten constraints, remove the compatibility code | only after N has run everywhere and N-1 can no longer be rolled back to |

Rules for reviewers of any change under `services/control-plane/src/nexora_control_plane/migrations/`:

* no destructive statement in the same release that stops using the data;
* no long exclusive locks on large tables without a plan;
* migrations are forward-only in production: `downgrade()` is for development, **never** the
  rollback mechanism;
* each migration must run on an empty database and on a copy of production-like data in CI.

## Upgrade: Docker Compose

```bash
cd deploy/compose
# 1. backup (see backup-restore.md), then record the current tag for rollback
grep '^NEXORA_IMAGE_TAG=' .env
# 2. set the new immutable tag
sed -i 's/^NEXORA_IMAGE_TAG=.*/NEXORA_IMAGE_TAG=<new-git-sha>/' .env
docker compose --env-file .env config -q
docker compose --env-file .env pull
# 3. `up -d` recreates migrate -> waits for it to complete -> recreates control-plane -> web
docker compose --env-file .env up -d
docker compose --env-file .env logs migrate        # must end with a successful migration
NEXORA_API_TOKEN=... python ../../tests/smoke/smoke.py --base-url http://127.0.0.1:8080 \
  --token-env NEXORA_API_TOKEN --wait-seconds 90
```

If `migrate` fails, `control-plane` is **not** started (`service_completed_successfully`) and the
old containers keep serving until recreated: investigate before retrying.

## Upgrade: Kubernetes (kustomize)

```bash
# the release workflow produced rendered.yaml for the overlay with owner + tag substituted
kubectl -n nexora delete job nexora-migrate --ignore-not-found      # Jobs are immutable
kubectl apply -f rendered.yaml
kubectl -n nexora wait --for=condition=complete job/nexora-migrate --timeout=10m
kubectl -n nexora rollout status deploy/control-plane --timeout=10m
kubectl -n nexora rollout status deploy/web --timeout=10m
```

The Deployments also roll out during `apply`; this is safe because migrations are expand-only
and the application tolerates the old schema until the Job finishes. If the Job fails, stop: do
not proceed; the old ReplicaSet keeps serving only if you also pause the rollout
(`kubectl rollout pause deploy/control-plane`) before applying when a migration is risky.

## Upgrade: Helm

```bash
helm upgrade nexora deploy/helm/nexora -n nexora --reuse-values \
  --set image.tag=<new-git-sha> --atomic --timeout 10m
```

The pre-upgrade hook Job runs the migration; a failed hook fails the upgrade and, with
`--atomic`, rolls the release back automatically.

## Rollback

### Application only (the normal case)

Safe when the failed release only contained expand-style migrations.

* **Compose:** set `NEXORA_IMAGE_TAG` back to the previous recorded SHA, `docker compose up -d`.
  The migrate step re-runs and is a no-op for an already-applied schema.
* **Kustomize:** re-render the overlay with the previous SHA and apply, or
  `kubectl -n nexora rollout undo deploy/control-plane deploy/web`.
* **Helm:** `helm rollback nexora <revision> -n nexora` (or `helm history nexora` to pick one).

### Database

The schema is **not** rolled back. If a release shipped a destructive/contract migration or the
data was damaged:

1. Stop traffic (`docker compose stop control-plane web` / scale deployments to 0).
2. Restore from the backup taken before the upgrade, into a new database, following
   `backup-restore.md` section 2.
3. Redeploy the previous image tag against the restored database.
4. Run the smoke test and record the incident (data written after the backup is lost: communicate it).

### Decision table

| Symptom | Action |
|---------|--------|
| migration step failed | fix forward or redeploy previous tag; DB unchanged if the migration is transactional |
| new version unhealthy, migration was expand-only | application rollback |
| new version corrupted data / destructive migration applied | database restore + previous tag |
| smoke test fails after upgrade | application rollback first, diagnose afterwards |
