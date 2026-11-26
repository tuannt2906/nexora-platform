# Adapter contract: Trino

| | |
|---|---|
| Engine kind | `trino` |
| Implementation | `nexora_modules.adapters.probes.TrinoAdapter` |
| Current maturity | **probe** |
| Domain port it will back | `nexora_modules.query.ports.QueryEngine` (not implemented by this adapter yet) |

## What this adapter does today

It answers one question: *is this engine endpoint alive and speaking the expected protocol?*
It does not execute queries, submit jobs, read or write data.

- **Probe:** `GET {endpoint}/v1/info` on the coordinator
- **Healthy:** HTTP 200, JSON object with `starting: false`
- **Degraded:** HTTP 200 but `starting: true`, or a non-JSON / non-object body; any non-2xx below 500
- **Unhealthy:** transport error (refused, timeout, DNS), or HTTP 5xx
- **Contract:** `health()` never raises for an unreachable engine; it reports `unhealthy`.

## Configuration (`ConnectionSpec`)

endpoint `http(s)://host:8080`; optional `probe_path`; credentials via `secret_ref` (not used by the probe yet). Secrets are referenced through `secret_ref`, never embedded.

## Verification status

| Level | Status |
|---|---|
| Unit/contract tests against a mocked transport | executed in CI: `packages/nexora-modules/tests/test_adapters_contract.py` |
| Probe path and response shape | taken from upstream documentation by the author; **not yet confirmed against a live engine** |
| Live engine in CI (integration suite) | **not done** (roadmap milestone M3) |

## Promotion to `functional`

Requires all of: the domain port above implemented by this adapter; a CI integration job that starts
the real engine and runs the shared port contract suite against it; documented failure mapping.
Next capability to implement: submit a statement through the Trino REST protocol (`POST /v1/statement`), page results, map errors.
