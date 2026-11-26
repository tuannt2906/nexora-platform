# Adapter contract: Apache Kafka

| | |
|---|---|
| Engine kind | `kafka` |
| Implementation | `nexora_modules.adapters.probes.KafkaAdapter` |
| Current maturity | **probe** |
| Domain port it will back | `nexora_modules.streaming.ports.StreamingPlatform` (not implemented by this adapter yet) |

## What this adapter does today

It answers one question: *is this engine endpoint alive and speaking the expected protocol?*
It does not execute queries, submit jobs, read or write data.

- **Probe:** TCP connect to the first host of `endpoint` (default port 9092)
- **Healthy:** TCP connection accepted
- **Degraded:** never reported: a TCP probe cannot observe partial degradation
- **Unhealthy:** transport error (refused, timeout, DNS), or HTTP 5xx
- **Contract:** `health()` never raises for an unreachable engine; it reports `unhealthy`.

## Configuration (`ConnectionSpec`)

endpoint `host[:port][,host[:port]...]`; no protocol handshake, no authentication. Secrets are referenced through `secret_ref`, never embedded.

## Verification status

| Level | Status |
|---|---|
| Unit/contract tests against a mocked transport | executed in CI: `packages/nexora-modules/tests/test_adapters_contract.py` |
| Probe path and response shape | taken from upstream documentation by the author; **not yet confirmed against a live engine** |
| Live engine in CI (integration suite) | **not done** (roadmap milestone M3) |

## Promotion to `functional`

Requires all of: the domain port above implemented by this adapter; a CI integration job that starts
the real engine and runs the shared port contract suite against it; documented failure mapping.
Next capability to implement: Kafka protocol client: metadata request, topic list/create/describe, authentication (SASL/mTLS).
