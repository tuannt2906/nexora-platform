# Contributing

1. Read [docs/engineering/conventions.md](docs/engineering/conventions.md) and the [ADRs](docs/adr/README.md).
2. `python tools/nx.py setup` once, then work on a branch.
3. Before opening a pull request run `python tools/nx.py check` (same gates as CI). Do not silence a failing
   gate; fix it or explain it in the PR.
4. Pull request checklist:
   - [ ] tests added/updated; no test was skipped or weakened to get green
   - [ ] OpenAPI snapshot and web types regenerated if the API changed
   - [ ] Alembic migration added if the database model changed
   - [ ] docs / ADR updated; maturity claims backed by evidence (ADR-0004)
   - [ ] no secrets, workstation paths or hardcoded hosts
5. Never claim a test passed that you did not run. Record what ran and what did not in the PR description.

Commit style: Conventional Commits. One coherent change per commit.

By contributing you agree that your contribution is licensed under the Apache License 2.0 (see `LICENSE`).
