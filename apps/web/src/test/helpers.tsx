import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { App } from '../App';
import { SessionProvider } from '../api/context';
import type {
  AdapterInfo,
  AuditEvent,
  ConnectionHealth,
  ConnectionOut,
  ModuleSpec,
  PlatformInfo,
} from '../api/types';

export const TOKEN = 'test-token-0123456789abcdef';

export const platform: PlatformInfo = {
  name: 'nexora-control-plane',
  version: '0.1.0',
  environment: 'test',
  git_sha: 'abc1234',
};

export const modules: ModuleSpec[] = [
  {
    id: 'ingestion',
    title: 'Batch ingestion',
    maturity: 'contract',
    summary: 'Reads batches from sources.',
    responsibilities: ['Describe source schemas'],
    public_interfaces: ['nexora_modules.ingestion.ports.IngestionSource'],
    engines: ['kafka'],
    config: [],
    depends_on: [],
    acceptance: [
      { id: 'ING-1', criterion: 'Fake satisfies the port', status: 'met' },
      { id: 'ING-2', criterion: 'Verified against a live engine', status: 'planned' },
      { id: 'ING-3', criterion: 'Retries are idempotent', status: 'unmet' },
    ],
  },
  {
    id: 'quality',
    title: 'Data quality',
    maturity: 'functional',
    summary: 'Evaluates rules.',
    responsibilities: ['Evaluate rules'],
    public_interfaces: ['nexora_modules.quality.ports.QualityEvaluator'],
    engines: [],
    config: [],
    depends_on: [],
    acceptance: [{ id: 'DQ-1', criterion: 'Rules work', status: 'met' }],
  },
];

export const adapters: AdapterInfo[] = [
  {
    kind: 'trino',
    display_name: 'Trino',
    maturity: 'probe',
    capabilities: ['health'],
    contract_doc: 'contracts/adapters/trino.md',
  },
];

export const connections: ConnectionOut[] = [
  {
    name: 'trino-main',
    kind: 'trino',
    endpoint: 'http://trino:8080',
    secret_ref: null,
    options: {},
    created_at: '2026-11-26T10:00:00Z',
  },
];

export const connectionHealth: ConnectionHealth[] = [
  {
    name: 'trino-main',
    kind: 'trino',
    maturity: 'probe',
    health: { state: 'healthy', detail: 'ok', checked_at: '2026-11-26T10:00:01Z' },
  },
];

export const audit: AuditEvent[] = [
  {
    occurred_at: '2026-11-26T10:00:00Z',
    actor: 'api-token',
    action: 'connection.created',
    target: 'trino-main',
    detail: { kind: 'trino' },
  },
];

export type Handler = (init: RequestInit) => Response | Promise<Response>;

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function apiError(status: number, code: string, message: string): Response {
  return json({ error: { code, message, details: {} } }, status);
}

/** Default happy-path routes; tests override single entries. Keys are "METHOD /path". */
export function defaultRoutes(): Record<string, Handler> {
  return {
    'GET /api/v1/platform': () => json(platform),
    'GET /api/v1/modules': () => json(modules),
    'GET /api/v1/adapters': () => json(adapters),
    'GET /api/v1/connections': () => json(connections),
    'GET /api/v1/health/connections': () => json(connectionHealth),
    'GET /api/v1/audit-events?limit=100': () => json(audit),
  };
}

export function mockFetch(routes: Record<string, Handler>) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const method = init?.method ?? 'GET';
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    const key = `${method} ${url}`;
    const handler = routes[key];
    if (!handler) return Promise.resolve(apiError(404, 'not_found', `no mock for ${key}`));
    return Promise.resolve(handler(init ?? {}));
  }) satisfies typeof fetch;
}

export function renderApp(fetchImpl: typeof fetch, path = '/', signedIn = true) {
  if (signedIn) sessionStorage.setItem('nexora.token', TOKEN);
  return render(
    <SessionProvider fetchImpl={fetchImpl}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </SessionProvider>,
  );
}
