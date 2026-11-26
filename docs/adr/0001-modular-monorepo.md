# 0001. Modular monorepo with enforced boundaries

Status: Accepted
Date: 2026-11-26

## Context

NEXORA spans a control plane, many domain modules, SDKs, a frontend, infrastructure and deployment
assets. These change together (an API change touches the service, the SDK, the frontend types and the
docs), so a single repository gives atomic changes and one CI. The risk is a "big ball of mud".

## Decision

One Git repository with explicit top-level areas:

| Area | Path | Rule |
|---|---|---|
| Kernel | `packages/nexora-core` | no knowledge of any engine or service |
| Domain modules + adapters | `packages/nexora-modules` | depend on core only; modules never import each other or the adapters |
| Control Plane | `services/control-plane` | the only place that wires modules, adapters, settings and persistence |
| SDK | `sdk/python` | independent of server internals; talks HTTP only |
| Frontend | `apps/web` | talks to the API through types generated from the OpenAPI contract |
| Contracts | `contracts/` | OpenAPI snapshot, adapter contract documents |
| Infrastructure / Deployment | `infra/`, `deploy/` | image build contexts; compose, Kubernetes, Helm |
| Tests | per package, `tests/` | unit next to code; cross-service and smoke tests at the root |

Boundaries are executable: `import-linter` contracts in `pyproject.toml` (layers, independence of modules,
SDK isolation, modules-must-not-import-adapters) run in `make validate`. Every domain module carries a
`module.toml` with responsibilities, public interfaces, dependencies, configuration and acceptance criteria;
a test verifies the descriptor against the code.

## Consequences

Boundary violations fail CI instead of being discovered in review. A new module needs a descriptor, port,
fake and contract test before it can be listed. Cost: slightly more ceremony per module.
