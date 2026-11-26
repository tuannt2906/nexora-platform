import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import {
  TOKEN,
  apiError,
  defaultRoutes,
  json,
  mockFetch,
  platform,
  renderApp,
} from './test/helpers';

describe('token gate', () => {
  it('shows the token screen when signed out', () => {
    renderApp(mockFetch(defaultRoutes()), '/', false);
    expect(screen.getByLabelText('API token')).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('rejects a wrong token without storing it', async () => {
    const routes = defaultRoutes();
    routes['GET /api/v1/platform'] = () => apiError(401, 'unauthorized', 'bad');
    renderApp(mockFetch(routes), '/', false);
    await userEvent.type(screen.getByLabelText('API token'), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('rejected');
    expect(sessionStorage.getItem('nexora.token')).toBeNull();
  });

  it('shows non-auth errors from the login check', async () => {
    const routes = defaultRoutes();
    routes['GET /api/v1/platform'] = () => apiError(500, 'internal_error', 'boom');
    renderApp(mockFetch(routes), '/', false);
    await userEvent.type(screen.getByLabelText('API token'), 'x');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
  });

  it('accepts a valid token, keeps it in sessionStorage and loads the overview', async () => {
    const fetchImpl = mockFetch(defaultRoutes());
    renderApp(fetchImpl, '/', false);
    await userEvent.type(screen.getByLabelText('API token'), TOKEN);
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument();
    expect(sessionStorage.getItem('nexora.token')).toBe(TOKEN);
    expect(await screen.findByText(platform.version)).toBeInTheDocument();
  });

  it('signs out back to the token screen', async () => {
    renderApp(mockFetch(defaultRoutes()));
    await screen.findByRole('heading', { name: 'Overview' });
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(await screen.findByLabelText('API token')).toBeInTheDocument();
    expect(sessionStorage.getItem('nexora.token')).toBeNull();
  });

  it('returns to the token screen when the API answers 401 mid-session', async () => {
    const routes = defaultRoutes();
    routes['GET /api/v1/modules'] = () => apiError(401, 'unauthorized', 'expired');
    renderApp(mockFetch(routes), '/modules');
    expect(await screen.findByLabelText('API token')).toBeInTheDocument();
    expect(sessionStorage.getItem('nexora.token')).toBeNull();
  });
});

describe('overview', () => {
  it('summarises modules, adapters and connection health', async () => {
    renderApp(mockFetch(defaultRoutes()));
    const mods = await screen.findByRole('region', { name: 'Domain modules' });
    await waitFor(() => {
      expect(mods).toHaveTextContent('2 modules');
    });
    const adp = await screen.findByRole('region', { name: 'Engine adapters' });
    await waitFor(() => {
      expect(adp).toHaveTextContent('1 adapters');
    });
    const health = await screen.findByRole('region', { name: 'Connection health' });
    await waitFor(() => {
      expect(health).toHaveTextContent('1 healthy');
    });
  });

  it('says so when there are no connections', async () => {
    const routes = defaultRoutes();
    routes['GET /api/v1/health/connections'] = () => json([]);
    renderApp(mockFetch(routes));
    expect(await screen.findByText(/No engine connections registered/)).toBeInTheDocument();
  });

  it('renders an error with retry when a request fails', async () => {
    const routes = defaultRoutes();
    routes['GET /api/v1/platform'] = () => apiError(500, 'internal_error', 'kaput');
    renderApp(mockFetch(routes));
    const alerts = await screen.findAllByRole('alert');
    expect(alerts[0]).toHaveTextContent('kaput');
    expect(screen.getAllByRole('button', { name: 'Retry' }).length).toBeGreaterThan(0);
  });

  it('redirects unknown routes to the overview', async () => {
    renderApp(mockFetch(defaultRoutes()), '/nope');
    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument();
  });
});
