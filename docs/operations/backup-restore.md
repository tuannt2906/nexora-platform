# Backup and restore (PostgreSQL)

Scope: the Control Plane database (connection registry, audit events, migration state). It is the
only stateful component in this milestone. Logical backups with `pg_dump` custom format.

> Status: the procedure below is written but has **not yet been executed against a real
> deployment**. Perform the restore drill (bottom of this page) before relying on it and record
> the result in `docs/status/`.

Fill these in for your environment and review them quarterly:

| Objective | Value |
|-----------|-------|
| RPO (max tolerated data loss) | e.g. 24 h with daily dumps |
| RTO (max tolerated downtime) | e.g. 1 h |
| Retention | e.g. 7 daily + 4 weekly + 6 monthly |

## 1. Take a backup

### Docker Compose

```bash
cd deploy/compose
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
docker compose --env-file .env exec -T postgres \
  pg_dump --username nexora --dbname nexora --format=custom --no-owner --no-privileges \
  > "nexora-${STAMP}.dump"
# verify the archive is readable and non-trivial
docker compose --env-file .env exec -T postgres pg_restore --list < "nexora-${STAMP}.dump" | head
sha256sum "nexora-${STAMP}.dump" > "nexora-${STAMP}.dump.sha256"
```

### Kubernetes / managed Postgres

Run from a host or a throw-away pod that has `postgresql-client-16` and network access to the
database. The application URL uses the SQLAlchemy scheme; strip `+psycopg` for libpq tools:

```bash
DB_URL=$(kubectl -n nexora get secret nexora-secrets -o jsonpath='{.data.NEXORA_DATABASE_URL}' \
  | base64 -d | sed 's/^postgresql+psycopg:/postgresql:/')
pg_dump "$DB_URL" --format=custom --no-owner --no-privileges > "nexora-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Managed services usually also offer snapshots / PITR; use them **in addition** to logical dumps
(dumps are portable across providers and versions, snapshots give faster restore and PITR).

### After taking it

1. Encrypt before it leaves the host (`age -r <recipient> file` or `gpg --encrypt`).
2. Copy to storage in a **different failure domain** (another account/region/provider).
3. Enforce retention; never let the only copy live on the database host.
4. Alert if the newest backup is older than 1.5x the interval.

## 2. Restore

Always restore into a **new, empty database first** and verify, then switch traffic.

### Docker Compose (restore into a scratch database)

```bash
cd deploy/compose
docker compose --env-file .env exec -T postgres createdb --username nexora nexora_restore
docker compose --env-file .env exec -T postgres \
  pg_restore --username nexora --dbname nexora_restore --no-owner --exit-on-error < nexora-<STAMP>.dump
docker compose --env-file .env exec -T postgres psql --username nexora --dbname nexora_restore \
  -c "SELECT version_num FROM alembic_version;"
```

To cut over (this is downtime):

```bash
docker compose --env-file .env stop control-plane web
docker compose --env-file .env exec -T postgres psql --username nexora --dbname postgres -c \
  "ALTER DATABASE nexora RENAME TO nexora_old; ALTER DATABASE nexora_restore RENAME TO nexora;"
docker compose --env-file .env up -d
```

Keep `nexora_old` until the smoke test passes, then drop it. If rename fails because of open
connections, stop the services first (done above) and retry.

### Kubernetes / managed Postgres

Restore to a new database (`createdb`, `pg_restore --dbname <new>` against `$DB_URL` pointing at
the new database), update the `database-url` entry in the external secret manager, wait for the
ExternalSecret refresh (or `kubectl annotate externalsecret nexora-secrets force-sync=$(date +%s) --overwrite`),
then `kubectl -n nexora rollout restart deploy/control-plane`.

## 3. After every restore

1. `alembic_version` matches what the deployed image expects. If the dump is **older** than the
   deployed image, run the migration step (compose: `docker compose up migrate`; k8s: the
   migration Job). Never run a newer schema under an older image.
2. Run the smoke test (`runbook-smoke.md`).
3. Record the incident/drill: date, backup used, data loss window, time to recover.

## 4. Restore drill checklist (do this before go-live and then quarterly)

- [ ] Pick the most recent production backup (not a fresh one made for the drill).
- [ ] Decrypt it on a machine that is **not** the database host.
- [ ] Restore into an isolated database/stack.
- [ ] `pg_restore --list` shows all expected tables; `alembic_version` is current.
- [ ] Start the application image of the same release against the restored database; smoke test passes.
- [ ] Sample records (connections, audit events) match expectations.
- [ ] Measured restore time <= RTO; backup age <= RPO. If not, fix the process, not the target.
- [ ] Result recorded with date and operator.
