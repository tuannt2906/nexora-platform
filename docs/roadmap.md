# Implementation roadmap

Each milestone ends with: code, tests run locally and in CI, updated documentation, recorded evidence in
`docs/status/TEST_EVIDENCE.md`, updated `PROJECT_STATUS.md`, and coherent commits. A milestone is not "done"
until its exit criteria are demonstrated, not merely configured.

| # | Milestone | Scope | Exit criteria |
|---|---|---|---|
| **M0** | **Foundation** (this repository state) | monorepo, ADRs, conventions, control plane (connections, audit, health, metrics, migrations), 12 module ports with fakes, 10 engine probe adapters, SDK, React UI, CI/CD workflows, deploy assets, quality gates | all local gates pass; workflows lint clean; CI-only items listed honestly |
| **M0.5** | **First run in GitHub** | push, enable branch protection and secret scanning, fix whatever CI finds | all PR workflows green on `main`; images built, scanned, SBOM produced |
| **M1** | **Identity and access** | OIDC login, service tokens, RBAC through the governance policy port, real audit actors (ADR-0006) | e2e test: unauthenticated and unauthorized requests rejected; audit shows subject |
| **M2** | **First server deployment** | deploy via compose on the dedicated server, TLS, backups scheduled, restore drill executed, upgrade + rollback rehearsed | smoke test green on the server; drill record committed |
| **M3** | **Live-engine integration harness** | CI jobs that start real engines (MinIO, Iceberg REST catalog, Trino first) and run the shared port contract suites; promote probes to verified; first `functional` adapters (Trino `QueryEngine`, Iceberg `TableCatalog`, S3 `ObjectStore`) | contract suites pass against real engines in CI; maturity promoted with evidence |
| **M4** | **Streaming and CDC** | Kafka, Kafka Connect/Debezium adapters functional (`StreamingPlatform`, `CdcConnectorManager`), schema/topic management | CDC from a test Postgres into a Kafka topic verified in CI |
| **M5** | **Processing and orchestration** | Flink and Spark job submission/status (`ProcessingEngine`), Airflow `Orchestrator`, ingestion jobs writing Iceberg | end-to-end batch + streaming job into an Iceberg table, queried through Trino, in CI |
| **M6** | **Governance, quality, lineage** | policy decisions enforced on API paths, quality rules scheduled against tables, OpenLineage events emitted by jobs | policy denial test; failing quality rule surfaces in the API; lineage graph queryable |
| **M7** | **Observability and AI extensions** | Prometheus query adapter, dashboards/alerts shipped as code, `EmbeddingProvider`/`LlmGateway` adapters | alert rules unit-tested; AI adapters behind a feature flag with contract tests |
| **M8** | **Production readiness** | HA topology, load and failure tests, SLOs, security review, DR exercise | documented SLOs met in a test; threat-model review recorded |

## Known limitations carried by M0

- No engine adapter is above `probe`; no domain port is backed by a real engine.
- Authentication is a single shared token (ADR-0006).
- Images, Helm rendering, the integration job, the release and deploy workflows have not run yet.
- The Python lock file was resolved on Windows; CI installs it on Linux and will expose any gap.
- `CODEOWNERS` contains no owners until real handles are filled in.
