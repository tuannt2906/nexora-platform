# 0007. Dependency pinning and supply-chain controls

Status: Accepted
Date: 2026-11-26

## Decision

- **Python:** direct dependencies are declared in `requirements/*.in`; `requirements/prod.txt` and
  `requirements/dev.txt` are compiled with exact versions and sha256 hashes (`make lock`) and installed with
  `pip install --require-hashes`. The production image installs only from `prod.txt`.
- **Node:** `apps/web/package-lock.json` is committed, `.npmrc` sets `save-exact`, CI uses `npm ci`.
- **GitHub Actions:** every `uses:` is pinned to a full commit SHA with the version in a comment; a policy
  check fails the build otherwise. Dependabot proposes updates weekly.
- **Container images:** base images use exact version tags (never `latest`; a check enforces it) and the
  release workflow resolves and records their digests. Application images are tagged with the full git SHA
  (immutable) and the release version; deployments reference the SHA.
- **Scanning:** `pip-audit`, `npm audit`, `bandit`, `detect-secrets` (all in `make security-check`), Trivy
  image and configuration scans, CycloneDX/SPDX SBOMs and CodeQL (public repositories) in CI.
- **Workflow safety:** least-privilege `permissions:` per workflow, no `pull_request_target`, credentials not
  persisted in checkouts, release only from tags reachable from `main`.

## Consequences

Updates are explicit PRs that CI validates. Lock files are generated on Windows; `uvloop`-style
Linux-only extras are avoided so the lock is complete for Linux, and CI installs from it on Linux to prove it.
Digest pinning of base images happens at release time rather than in the repository (to be revisited once the
registry is reachable from the build environment).
