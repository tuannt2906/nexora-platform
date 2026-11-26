# 0010. Database migration policy (expand/contract)

Status: Accepted
Date: 2026-11-26

## Decision

- Schema is owned by Alembic migrations packaged inside the service
  (`services/control-plane/src/nexora_control_plane/migrations`). There is no `alembic.ini` on disk.
- Migrations run as a separate one-shot step before the new application version starts
  (`python -m nexora_control_plane.migrate`): a compose one-shot service, or a Helm pre-install/pre-upgrade
  hook Job. The application never migrates itself on startup.
- **Expand/contract:** a release may only *add* nullable columns/tables/indexes (expand). Dropping or
  renaming happens in a later release, after no running version uses the old shape (contract). Therefore the
  previous application version always runs against the new schema, which is what makes application rollback
  safe without a database restore.
- A unit test fails when the ORM models and the migration chain disagree (`test_migrations_match_orm_models`);
  an integration test applies migrations to real PostgreSQL in CI.
- Destructive or irreversible migrations require a documented backup point first
  (`docs/operations/backup-restore.md`).

## Consequences

Rollback of the application is an image-tag change. Rollback of data after a contract migration is a restore
from backup, which is why contract migrations are rare and reviewed.
