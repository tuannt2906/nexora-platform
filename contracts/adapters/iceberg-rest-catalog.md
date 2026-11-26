# Adapter contract: Iceberg REST Catalog

| | |
|---|---|
| Engine kind | `iceberg-rest-catalog` |
| Implementation | `nexora_modules.adapters.probes.IcebergRestCatalogAdapter` |
| Current maturity | **probe** |
| Domain port it will back | `nexora_modules.lakehouse.ports.TableCatalog` (not implemented by this adapter yet) |

## What this adapter does today

It answers one question: *is this engine endpoint alive and speaking the expected protocol?*
It does not execute queries, submit jobs, read or write data.

- **Probe:** `GET {endpoint}/v1/config`
- **Healthy:** HTTP 200, JSON object containing `defaults` and `overrides`
- **Degraded:** HTTP 200 with a body that is not an Iceberg catalog configuration; any non-2xx below 500
- **Unhealthy:** transport error (refused, timeout, DNS), or HTTP 5xx
- **Contract:** `health()` never raises for an unreachable engine; it reports `unhealthy`.

## Configuration (`ConnectionSpec`)

endpoint `http(s)://host:8181`; optional `probe_path` (some catalogs prefix the API path). Secrets are referenced through `secret_ref`, never embedded.

## Verification status

| Level | Status |
|---|---|
| Unit/contract tests against a mocked transport | executed in CI: `packages/nexora-modules/tests/test_adapters_contract.py` |
| Probe path and response shape | taken from upstream documentation by the author; **not yet confirmed against a live engine** |
| Live engine in CI (integration suite) | **not done** (roadmap milestone M3) |

## Promotion to `functional`

Requires all of: the domain port above implemented by this adapter; a CI integration job that starts
the real engine and runs the shared port contract suite against it; documented failure mapping.
Next capability to implement: list namespaces/tables and load table metadata per the Iceberg REST catalog specification.
