# Runbook: deployment smoke test

Run after **every** deployment, upgrade, rollback and restore. Source: `tests/smoke/smoke.py`
(Python standard library only, so it runs on any server with Python 3.11+).

```bash
export NEXORA_API_TOKEN=...            # from your secret manager, never on the command line
python tests/smoke/smoke.py --base-url https://nexora.example.com --token-env NEXORA_API_TOKEN \
  --wait-seconds 90
```

Exit code `0` = all checks passed, `1` = at least one failed, `2` = usage/config error.

## What it checks

| Check | Proves | If it fails |
|-------|--------|-------------|
| `GET /healthz` -> 200 | process is up and serving HTTP through the whole path (proxy/ingress -> web -> api) | check pods/containers, ingress, TLS, DNS |
| `GET /readyz` -> 200 | the API can reach PostgreSQL | check `NEXORA_DATABASE_URL`, DB reachability, NetworkPolicy egress 5432, migrations ran |
| `GET /metrics` shows Prometheus text | metrics endpoint is wired (alerting can work) | check the route is not blocked by the proxy |
| `GET /api/v1/platform` **without** token -> 401 | authentication is actually enforced | **stop and escalate**: the API may be open |
| `GET /api/v1/platform` **with** token -> 200 JSON with `version` | the secret, the API and the response contract agree | token mismatch between secret manager and pods; check `NEXORA_API_TOKEN` rollout |

Use `--base-url` of the public hostname for a true end-to-end check; use
`kubectl port-forward svc/<web> 8080:80` and `http://127.0.0.1:8080` when validating before
exposing a release.

## What it does NOT prove

A passing smoke test means the deployment is *wired*; it is **not** proof of production
readiness. Separately confirm (and record) before go-live:

- [ ] a backup was taken and a **restore drill** succeeded (`backup-restore.md`);
- [ ] TLS certificate valid and auto-renewing; HSTS as required;
- [ ] alerts fire (kill a pod/stop the DB in staging and see the page);
- [ ] resource limits are sized from load testing, not from defaults;
- [ ] dependency/container/secret scans of this exact image tag were green in CI;
- [ ] the previous release tag is recorded for rollback, and rollback was rehearsed in staging;
- [ ] each external engine connection reports a healthy status from `/api/v1/connections/<name>/health`.

## Interpreting results in automation

* The release workflow runs the smoke test against `staging` automatically and blocks promotion
  to `production` on a non-zero exit.
* After production deployment run it once more; on failure, execute the rollback decision table
  in `upgrade-rollback.md` first and investigate afterwards.
