# Architecture Decision Records

Decisions that shape the platform are recorded here, one file per decision, numbered and immutable
once accepted (supersede with a new ADR instead of editing history). Template: [0000-template.md](0000-template.md).

| ADR | Title | Status |
|---|---|---|
| [0001](0001-modular-monorepo.md) | Modular monorepo with enforced boundaries | Accepted |
| [0002](0002-technology-baseline.md) | Technology baseline: Python control plane, React frontend, PostgreSQL | Accepted |
| [0003](0003-development-to-production-model.md) | Workstation → Git → CI/CD → registry → server | Accepted |
| [0004](0004-engine-adapters-and-maturity.md) | Third-party engines behind adapters; honest maturity levels | Accepted |
| [0005](0005-quality-gates.md) | One task runner, identical gates locally and in CI | Accepted |
| [0006](0006-authentication-and-authorization.md) | Authentication and authorization roadmap | Proposed |
| [0007](0007-supply-chain-and-pinning.md) | Dependency pinning and supply-chain controls | Accepted |
| [0008](0008-configuration-and-secrets.md) | Configuration from environment; secrets outside the repository | Accepted |
| [0009](0009-data-platform-target-architecture.md) | Data platform target architecture | Proposed |
| [0010](0010-database-migrations.md) | Database migration policy (expand/contract) | Accepted |
