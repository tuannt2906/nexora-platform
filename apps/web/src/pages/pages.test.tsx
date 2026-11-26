import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { connections, defaultRoutes, json, mockFetch, renderApp } from '../test/helpers';
import { validateConnection } from './validation';

describe('Modules page', () => {
  it('lists modules with maturity and criteria progress', async () => {
    renderApp(mockFetch(defaultRoutes()), '/modules');
    const item = (await screen.findByText('Batch ingestion')).closest('li');
    expect(item).not.toBeNull();
    const scope = within(item as HTMLElement);
    expect(scope.getByText('contract')).toBeInTheDocument();
    expect(scope.getByText('1/3 criteria met')).toBeInTheDocument();
    expect(scope.getByRole('img', { name: '1 met, 1 unmet, 1 planned' })).toBeInTheDocument();
    expect(scope.getByText('ING-3')).toBeInTheDocument();
    expect(scope.getByText('nexora_modules.ingestion.ports.IngestionSource')).toBeInTheDocument();
    expect(scope.getByText('kafka')).toBeInTheDocument();
    expect(screen.getByText('functional')).toBeInTheDocument();
  });
});

describe('Adapters page', () => {
  it('labels probe adapters as not functional', async () => {
    renderApp(mockFetch(defaultRoutes()), '/adapters');
    expect(await screen.findByRole('note')).toHaveTextContent(/NOT verified against a live engine/);
    expect(await screen.findByText('Trino')).toBeInTheDocument();
    expect(screen.getByText('contracts/adapters/trino.md')).toBeInTheDocument();
  });
});

describe('Audit page', () => {
  it('shows events', async () => {
    renderApp(mockFetch(defaultRoutes()), '/audit');
    expect(await screen.findByText('connection.created')).toBeInTheDocument();
  });

  it('shows an empty state', async () => {
    const routes = defaultRoutes();
    routes['GET /api/v1/audit-events?limit=100'] = () => json([]);
    renderApp(mockFetch(routes), '/audit');
    expect(await screen.findByText(/No audit events/)).toBeInTheDocument();
  });
});

describe('Connections page', () => {
  it('lists connections with health', async () => {
    renderApp(mockFetch(defaultRoutes()), '/connections');
    expect(await screen.findByText('trino-main')).toBeInTheDocument();
    expect(await screen.findByText('healthy')).toBeInTheDocument();
  });

  it('shows an empty state', async () => {
    const routes = defaultRoutes();
    routes['GET /api/v1/connections'] = () => json([]);
    renderApp(mockFetch(routes), '/connections');
    expect(await screen.findByText(/No connections registered yet/)).toBeInTheDocument();
  });

  it('marks health as unavailable when the health call fails', async () => {
    const routes = defaultRoutes();
    routes['GET /api/v1/health/connections'] = () =>
      json({ error: { code: 'x', message: 'y' } }, 500);
    renderApp(mockFetch(routes), '/connections');
    expect(await screen.findByText('unavailable')).toBeInTheDocument();
  });

  it('validates the form client-side before calling the API', async () => {
    const fetchImpl = mockFetch(defaultRoutes());
    renderApp(fetchImpl, '/connections');
    await screen.findByText('trino-main');
    await userEvent.type(screen.getByLabelText('Name'), 'Bad Name');
    await userEvent.click(screen.getByRole('button', { name: 'Register connection' }));
    expect(screen.getByText(/lowercase letters, digits and hyphens/)).toBeInTheDocument();
    expect(screen.getByText('Endpoint is required.')).toBeInTheDocument();
    expect(fetchImpl).not.toHaveBeenCalledWith(
      '/api/v1/connections',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('creates a connection and refreshes the list', async () => {
    const routes = defaultRoutes();
    let posted: unknown;
    routes['POST /api/v1/connections'] = (init) => {
      posted = JSON.parse(init.body as string);
      return json(
        { ...(posted as object), secret_ref: 'k8s://ns/x', options: {}, created_at: 'now' },
        201,
      );
    };
    renderApp(mockFetch(routes), '/connections');
    await screen.findByText('trino-main');
    await userEvent.selectOptions(screen.getByLabelText('Engine kind'), 'flink');
    await userEvent.type(screen.getByLabelText('Name'), 'flink-a');
    await userEvent.type(screen.getByLabelText('Endpoint'), 'http://flink:8081');
    await userEvent.type(screen.getByLabelText('Secret reference (optional)'), 'k8s://ns/x');
    await userEvent.click(screen.getByRole('button', { name: 'Register connection' }));
    expect(await screen.findByText('Connection registered.')).toBeInTheDocument();
    expect(posted).toEqual({
      kind: 'flink',
      name: 'flink-a',
      endpoint: 'http://flink:8081',
      secret_ref: 'k8s://ns/x',
    });
    expect(screen.getByLabelText('Name')).toHaveValue('');
  });

  it('shows the API error when creation fails', async () => {
    const routes = defaultRoutes();
    routes['POST /api/v1/connections'] = () =>
      json(
        { error: { code: 'conflict', message: "connection 'a' already exists", details: {} } },
        409,
      );
    renderApp(mockFetch(routes), '/connections');
    await screen.findByText('trino-main');
    await userEvent.type(screen.getByLabelText('Name'), 'a');
    await userEvent.type(screen.getByLabelText('Endpoint'), 'trino:8080');
    await userEvent.click(screen.getByRole('button', { name: 'Register connection' }));
    expect(await screen.findByText(/already exists \(conflict\)/)).toBeInTheDocument();
  });

  it('deletes after an explicit confirmation', async () => {
    const routes = defaultRoutes();
    let deleted = false;
    routes['GET /api/v1/connections'] = () => json(deleted ? [] : connections);
    routes['DELETE /api/v1/connections/trino-main'] = () => {
      deleted = true;
      return new Response(null, { status: 204 });
    };
    renderApp(mockFetch(routes), '/connections');
    await userEvent.click(await screen.findByRole('button', { name: 'Delete trino-main' }));
    expect(deleted).toBe(false);
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    await userEvent.click(screen.getByRole('button', { name: 'Delete trino-main' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm delete trino-main' }));
    expect(await screen.findByText(/No connections registered yet/)).toBeInTheDocument();
    expect(deleted).toBe(true);
  });

  it('shows delete errors', async () => {
    const routes = defaultRoutes();
    routes['DELETE /api/v1/connections/trino-main'] = () =>
      json({ error: { code: 'not_found', message: 'gone', details: {} } }, 404);
    renderApp(mockFetch(routes), '/connections');
    await userEvent.click(await screen.findByRole('button', { name: 'Delete trino-main' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm delete trino-main' }));
    expect(await screen.findByText(/gone \(not_found\)/)).toBeInTheDocument();
  });
});

describe('validateConnection', () => {
  const ok = { name: 'trino-main', endpoint: 'http://trino:8080', secretRef: '' };
  it('accepts valid input', () => {
    expect(validateConnection(ok)).toEqual({});
    expect(validateConnection({ ...ok, endpoint: 'kafka:9092,kafka2:9092' })).toEqual({});
  });
  it.each(['-a', 'a-', 'A', 'a_b', ''])('rejects name %j', (name) => {
    expect(validateConnection({ ...ok, name }).name).toBeDefined();
  });
  it('rejects long names, bad schemes, bad endpoints and long refs', () => {
    expect(validateConnection({ ...ok, name: 'a'.repeat(64) }).name).toMatch(/63/);
    expect(validateConnection({ ...ok, endpoint: 'file:///etc/passwd' }).endpoint).toMatch(/http/);
    expect(validateConnection({ ...ok, endpoint: 'bad endpoint' }).endpoint).toMatch(/host/);
    expect(validateConnection({ ...ok, secretRef: 'x'.repeat(513) }).secretRef).toBeDefined();
  });
});
