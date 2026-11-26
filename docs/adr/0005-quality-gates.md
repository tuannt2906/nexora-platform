# 0005. One task runner, identical gates locally and in CI

Status: Accepted
Date: 2026-11-26

## Context

The developer workstation runs Windows without `make`; CI and servers run Linux. Gate logic duplicated in a
Makefile, PowerShell and YAML drifts, and "works on my machine" gates give false confidence.

## Decision

- All gate logic lives in `tools/nx.py` (standard library only). The `Makefile` targets are one-line calls
  into it; CI calls `make`. Windows users run `python tools/nx.py <target>`.
- Required targets: `lint`, `typecheck`, `test`, `test-unit`, `test-contract`, `validate`, `build`,
  `security-check` (plus `test-integration`, `docker-build`, `setup`, `lock`, `openapi-update`, `check`).
- Every step executes a real tool and propagates its exit code. The summary lists passed, failed and
  **skipped** steps.
- A missing tool is never a silent pass: locally it is a loud `SKIP` (listed as "NOT verified here"); with
  `CI=true` it is a failure. `NX_ONLY=python|web` narrows language-specific gates so per-stack CI jobs
  stay independent.
- Gates that need infrastructure the workstation does not have (Docker daemon, PostgreSQL, Trivy) are
  CI-only and are labelled as such, never reported as passed.

## Consequences

One place to change a gate. The runner itself is type-checked and unit-tested. Cost: contributors must
read `nx.py` rather than a Makefile to see exact commands (each step prints its command line).
