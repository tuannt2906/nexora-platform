# 0009. Data platform target architecture

Status: Proposed
Date: 2026-11-26

## Context

NEXORA must orchestrate and govern a lakehouse built from independent engines. The control plane should
manage and observe them without becoming a data path itself.

## Decision (target state; most of it is NOT implemented yet — see `docs/status/PROJECT_STATUS.md`)

```
 sources ──► Debezium on Kafka Connect ──► Kafka ──► Flink (streaming) ──┐
    │                                                                   ▼
    └──── batch ingestion ───────────────────────────► Spark (batch) ──► Iceberg tables on object storage
                                                                         │      (REST catalog)
                                                              Trino ◄────┘
 Orchestration (Airflow) · Lineage (OpenLineage) · Quality · Governance · Observability (Prometheus) · AI
```

- **Data plane vs control plane:** engines move and transform data; NEXORA registers connections, submits and
  observes work, enforces policy, records audit/lineage and exposes status. No row of business data flows
  through the control plane.
- **Contracts:** each engine is an adapter (ADR-0004) with a contract document; each capability is a domain
  port with a shared contract test suite.
- **Table format and catalog:** Apache Iceberg with a REST catalog on S3-compatible object storage.
- **Deployment of engines:** engines are deployed and sized by their own operators/charts on dedicated servers;
  this repository ships NEXORA's own services and the adapters. Compose/Helm here deliberately do not bundle a
  fifteen-engine stack presented as working.
- **Open questions** (to be decided before M4): Flink/Spark submission mechanism (REST vs Kubernetes
  operators), catalog implementation (Polaris/Nessie/Lakekeeper), secret resolution protocol for `secret_ref`.

## Consequences

Each engine reaches `functional` through its own milestone with a CI job running the real engine. Until then
the UI and API show `probe` or `contract`, not "integrated".
