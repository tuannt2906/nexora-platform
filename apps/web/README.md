# NEXORA web console

React 19 + TypeScript (strict) + Vite single-page app for the NEXORA Control Plane.
It talks only to the Control Plane HTTP API, always **same-origin** under `/api` (no host is ever
hardcoded). Requires Node >= 22 (developed on Node 24).

## Commands (run in `apps/web`)

| Command                 | What it does                                                                 |
| ----------------------- | ---------------------------------------------------------------------------- |
| `npm ci`                | Install the exact locked dependencies                                        |
| `npm run dev`           | Dev server; set `VITE_DEV_API_TARGET=http://<api-host>:8000` to proxy `/api` |
| `npm run lint`          | ESLint (typescript-eslint strict-type-checked), zero warnings allowed        |
| `npm run format:check`  | Prettier check (`npm run format` rewrites)                                   |
| `npm run typecheck`     | `tsc --noEmit`                                                               |
| `npm test`              | Vitest + Testing Library, coverage thresholds enforced (see below)           |
| `npm run build`         | Typecheck, then production bundle into `dist/`                               |
| `npm run gen:api`       | Regenerate `src/api/schema.d.ts` from the OpenAPI contract                   |
| `npm run gen:api:check` | Fails (exit 1) if `schema.d.ts` drifts from the contract                     |

Coverage gate (vitest `coverage.thresholds`): lines/statements/functions >= 80 %, branches >= 70 %.
Generated types, test helpers and `main.tsx` are excluded.

## API types

`src/api/schema.d.ts` is **generated** from `contracts/openapi/control-plane.v1.json` and committed.
After an intentional API change:

```bash
python tools/nx.py openapi-update      # repo root: refresh the OpenAPI snapshot
npm run gen:api                         # apps/web: regenerate the TypeScript types
```

CI runs `gen:api:check`, so an API change without regenerated types fails the pull request.

## Structure

```
src/
  api/        client.ts (typed fetch wrapper + ApiError), context.tsx (session/token + react-query),
              hooks.ts, token.ts (sessionStorage only), types.ts, schema.d.ts (generated)
  components/ Layout, TokenScreen, Badges, QueryState
  pages/      Overview, Modules, Adapters, Connections, Audit (+ validation.ts)
  test/       setup + fetch-mock helpers
```

## Behaviour notes

- The bearer token is kept in `sessionStorage` only (cleared with the tab), is verified against
  `GET /api/v1/platform` at sign-in, is never logged, and any `401` clears it and returns to the
  token screen.
- **Maturity labels are honest.** `probe` adapters only answer a health check against a mocked
  protocol; they are _not_ verified against a live engine. The Adapters page says so explicitly.
- The connection form's `secret_ref` is a _reference_ into the external secret manager, never a
  secret; the form validation mirrors the API (name regex, http(s)/host:port endpoint).
- Styling is plain CSS with variables (light/dark via `prefers-color-scheme`), no UI kit, no
  fonts/CDN, so the strict CSP served by nginx (no `unsafe-inline`) is satisfied.

## Dependency decisions

All versions are pinned exactly (`.npmrc`: `save-exact=true`, `engine-strict=true`).

- **TypeScript 5.9.3 (not 7.0.2 / 6.0.x).** `typescript-eslint@8.74.0` declares peer
  `typescript <6.1.0` and `openapi-typescript@7.13.0` declares peer `typescript ^5.x`; only 5.x
  satisfies both without `--force`. Revisit when either tool widens its peer range.
- Everything else is the latest published major (Vite 8.4.0, Vitest 5.1.2, ESLint 10.15.0,
  React 19.3.1, react-router-dom 7.18.7, @tanstack/react-query 5.108.4, jsdom 31.0.1, ...) and
  resolves with no peer conflicts.

## Container

`infra/docker/web.Dockerfile` (build context = repo root) builds the bundle and serves it with
Alpine's `nginx` package (non-root uid 101, own `nginx.conf` and entrypoint) on port **8080** as a non-root user. nginx proxies `/api/` to
`NEXORA_API_UPSTREAM` (default `http://control-plane:8000`) and answers `/healthz` itself.
For a read-only root filesystem mount writable volumes at `/tmp` and `/etc/nginx/conf.d`.
