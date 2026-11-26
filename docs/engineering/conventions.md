# Engineering conventions

## Workflow

1. Branch from `main` (`feat/…`, `fix/…`, `docs/…`); open a pull request; CI must be green.
2. Commits are small and coherent. Use [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat(control-plane): …`, `fix(web): …`, `docs(adr): …`).
3. Run the gates before pushing: `python tools/nx.py check` (or `make check`). They are the same gates CI runs.
4. A change to the HTTP API must update `contracts/openapi/control-plane.v1.json`
   (`python tools/nx.py openapi-update`) and the generated frontend types in the same commit.
5. A change to the database model needs an Alembic migration in the same commit (a test enforces it).
6. Decisions with lasting consequences get an ADR (`docs/adr/`).

## Python

- Python 3.11, `ruff` (lint + format, line length 100), `mypy --strict`, `pytest`.
- Public surfaces are typed `Protocol`s/pydantic models. No `print` (use `structlog`). No naive datetimes.
- Errors: raise `nexora_core.errors.*`; the service maps them to the HTTP error envelope.
- Async code must not block the event loop: blocking database work in `def` endpoints or `run_in_threadpool`.
- Tests: unit tests beside the package; `@pytest.mark.contract` for contracts; `@pytest.mark.integration` for
  tests needing real services (never run implicitly). Warnings are errors.

## TypeScript

- Strict TypeScript, no `any`; ESLint with zero warnings; Prettier; Vitest + Testing Library.
- API access only through the generated types in `apps/web/src/api`; same-origin `/api`, no hardcoded hosts.

## Configuration and secrets

- Environment variables with the `NEXORA_` prefix only; secrets have no defaults and are `SecretStr`.
- Never commit `.env*` (except `*.example`), keys or tokens; `detect-secrets` and `make validate` enforce it.
- No workstation paths and no hardcoded `localhost` in application source (checked).

## Dependencies

- Add a Python dependency to `requirements/*.in`, then `make lock`; commit the regenerated `.txt` files.
- Add a Node dependency with `npm install --save-exact`; commit `package-lock.json`.
- Pin GitHub Actions to full commit SHAs; images to exact tags (never `latest`).

## Modules

A new domain module needs: `module.toml`, `ports.py`, `models.py`, `fakes.py`, a contract test, an entry in
`MODULE_IDS` and in the import-linter independence contract. Maturity claims must be backed by evidence
(ADR-0004).

## Line endings

LF everywhere in the repository (`.gitattributes` enforces it); Windows scripts (`*.ps1`, `*.cmd`) use CRLF.
