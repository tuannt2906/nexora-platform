# Adapter contract: Apache Airflow

| | |
|---|---|
| Engine kind | `airflow` |
| Implementation | `nexora_modules.adapters.probes.AirflowAdapter` |
| Current maturity | **probe** |
| Domain port it will back | `nexora_modules.orchestration.ports.Orchestrator` (not implemented by this adapter yet) |

## What this adapter does today

It answers one question: *is this engine endpoint alive and speaking the expected protocol?*
It does not execute queries, submit jobs, read or write data.

- **Probe:** `GET {endpoint}/health` (Airflow 2.x). Airflow 3 serves health under its API server: set option `probe_path`
- **Healthy:** HTTP 200 and every present component (`metadatabase`, `scheduler`) reports `healthy`
- **Degraded:** a component reports any other status, or a non-JSON body
- **Unhealthy:** transport error (refused, timeout, DNS), or HTTP 5xx
- **Contract:** `health()` never raises for an unreachable engine; it reports `unhealthy`.

## Configuration (`ConnectionSpec`)

endpoint `http(s)://host:8080`; optional `probe_path`. Secrets are referenced through `secret_ref`, never embedded.

## Verification status

| Level | Status |
|---|---|
| Unit/contract tests against a mocked transport | executed in CI: `packages/nexora-modules/tests/test_adapters_contract.py` |
| Probe path and response shape | taken from upstream documentation by the author; **not yet confirmed against a live engine** |
| Live engine in CI (integration suite) | **not done** (roadmap milestone M3) |

## Promotion to `functional`

Requires all of: the domain port above implemented by this adapter; a CI integration job that starts
the real engine and runs the shared port contract suite against it; documented failure mapping.
Next capability to implement: list DAGs, trigger runs and read run state through the stable REST API of the deployed major version.
