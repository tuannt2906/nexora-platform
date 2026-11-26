import { describe, expect, it, vi } from 'vitest';
import { ApiError, createApiClient } from './client';

function respond(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('api client', () => {
  it('sends the bearer token and parses JSON', async () => {
    const fetchImpl = vi.fn(() => Promise.resolve(respond(200, { name: 'cp' })));
    const api = createApiClient({ getToken: () => 'secret-token', fetchImpl });
    await expect(api.platform()).resolves.toEqual({ name: 'cp' });
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/v1/platform');
    expect((init.headers as Record<string, string>)['Authorization']).toBe('Bearer secret-token');
  });

  it('omits Authorization without a token and sends JSON bodies', async () => {
    const fetchImpl = vi.fn(() => Promise.resolve(respond(201, {})));
    const api = createApiClient({ getToken: () => null, fetchImpl });
    await api.createConnection({ kind: 'trino', name: 'a', endpoint: 'h:1' });
    const [, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers['Authorization']).toBeUndefined();
    expect(headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(init.body as string)).toEqual({ kind: 'trino', name: 'a', endpoint: 'h:1' });
  });

  it('maps the error envelope to ApiError', async () => {
    const fetchImpl = vi.fn(() =>
      Promise.resolve(
        respond(409, { error: { code: 'conflict', message: 'exists', details: { x: 1 } } }),
      ),
    );
    const api = createApiClient({ getToken: () => 't', fetchImpl });
    const error = await api.connections().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 409,
      code: 'conflict',
      message: 'exists',
      details: { x: 1 },
    });
  });

  it('calls onUnauthorized on 401', async () => {
    const onUnauthorized = vi.fn();
    const fetchImpl = vi.fn(() =>
      Promise.resolve(respond(401, { error: { code: 'unauthorized', message: 'no' } })),
    );
    const api = createApiClient({ getToken: () => 't', onUnauthorized, fetchImpl });
    await expect(api.platform()).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it('handles 204 with no body', async () => {
    const fetchImpl = vi.fn(() => Promise.resolve(new Response(null, { status: 204 })));
    const api = createApiClient({ getToken: () => 't', fetchImpl });
    await expect(api.deleteConnection('a b')).resolves.toBeUndefined();
    expect((fetchImpl.mock.calls[0] as unknown as [string])[0]).toBe('/api/v1/connections/a%20b');
  });

  it('falls back to a generic error for non-envelope bodies', async () => {
    const fetchImpl = vi.fn(() => Promise.resolve(new Response('<html>', { status: 502 })));
    const api = createApiClient({ getToken: () => 't', fetchImpl });
    await expect(api.modules()).rejects.toMatchObject({ status: 502, code: 'http_error' });
  });

  it('reports network failures', async () => {
    const fetchImpl = vi.fn(() => Promise.reject(new TypeError('failed to fetch')));
    const api = createApiClient({ getToken: () => 't', fetchImpl });
    await expect(api.adapters()).rejects.toMatchObject({ status: 0, code: 'network_error' });
  });

  it('requests audit events with a limit', async () => {
    const fetchImpl = vi.fn(() => Promise.resolve(respond(200, [])));
    const api = createApiClient({ getToken: () => 't', fetchImpl });
    await api.auditEvents(5);
    await api.connectionsHealth();
    expect((fetchImpl.mock.calls[0] as unknown as [string])[0]).toBe(
      '/api/v1/audit-events?limit=5',
    );
    expect((fetchImpl.mock.calls[1] as unknown as [string])[0]).toBe('/api/v1/health/connections');
  });
});
