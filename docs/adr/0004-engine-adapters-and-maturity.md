# 0004. Third-party engines behind adapters; honest maturity levels

Status: Accepted
Date: 2026-11-26

## Context

NEXORA integrates many engines. A configuration file, a compose service or a Docker image proves nothing
about whether an integration works. Dashboards that overstate readiness are a production risk.

## Decision

- Engines are reached only through `EngineAdapter` implementations registered by `EngineKind`. Domain
  modules depend on ports (`typing.Protocol`), never on engine client libraries.
- Each adapter has a documented contract in `contracts/adapters/<kind>.md`.
- Every adapter and module declares a **maturity**, and the API/UI display it verbatim:

| Level | Meaning | Evidence required |
|---|---|---|
| `planned` | nothing implemented | — |
| `contract` | port + in-memory fake + contract tests | tests in CI |
| `probe` | real adapter, health/capability probe only | tests against a mocked protocol |
| `functional` | implements the domain port | shared port contract suite passing against the **real engine** in CI |
| `production` | functional and operated | observed on a production environment |

- Promotion requires evidence; demotion is automatic if the evidence job is removed. Acceptance criteria in
  `module.toml` may be `met` only when `evidence` points at an existing test file.
- A module with no external engine (for example the built-in quality rule evaluator) may declare
  `functional` when its own logic is fully tested; this is checked by `test_module_catalog.py`.

## Consequences

At the time of writing **no engine adapter is above `probe`**. The control plane reports exactly that.
Moving an engine to `functional` is a deliberate milestone (roadmap M3 onward), not a documentation edit.
