# Adapter contract: Kafka Connect (Debezium runtime)

| | |
|---|---|
| Engine kind | `kafka-connect` |
| Implementation | `nexora_modules.adapters.probes.KafkaConnectAdapter` |
| Current maturity | **probe** |
| Domain port it will back | `nexora_modules.cdc.ports.CdcConnectorManager` (not implemented by this adapter yet) |

## What this adapter does today

It answers one question: *is this engine endpoint alive and speaking the expected protocol?*
It does not execute queries, submit jobs, read or write data.

- **Probe:** `GET {endpoint}/` on a Connect worker
- **Healthy:** HTTP 200, JSON object containing `version`
- **Degraded:** HTTP 200 with a body that is not a Connect root document; any non-2xx below 500
- **Unhealthy:** transport error (refused, timeout, DNS), or HTTP 5xx
- **Contract:** `health()` never raises for an unreachable engine; it reports `unhealthy`.

## Configuration (`ConnectionSpec`)

endpoint `http(s)://host:8083`; optional `probe_path`. Secrets are referenced through `secret_ref`, never embedded.

## Verification status

| Level | Status |
|---|---|
| Unit/contract tests against a mocked transport | executed in CI: `packages/nexora-modules/tests/test_adapters_contract.py` |
| Probe path and response shape | taken from upstream documentation by the author; **not yet confirmed against a live engine** |
| Live engine in CI (integration suite) | **not done** (roadmap milestone M3) |

## Promotion to `functional`

Requires all of: the domain port above implemented by this adapter; a CI integration job that starts
the real engine and runs the shared port contract suite against it; documented failure mapping.
Next capability to implement: deploy/status/remove connectors via `/connectors`, including Debezium connector configuration.
