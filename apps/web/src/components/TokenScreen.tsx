import { useState, type SubmitEvent } from 'react';
import { ApiError } from '../api/client';
import { useSession } from '../api/context';
import { errorMessage } from './QueryState';

export function TokenScreen() {
  const { login } = useSession();
  const [token, setToken] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(token.trim());
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? 'The token was rejected by the Control Plane.'
          : errorMessage(err),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="token-screen">
      <form onSubmit={(e) => void submit(e)} className="card" aria-labelledby="token-title">
        <h1 id="token-title">NEXORA Control Plane</h1>
        <p className="muted">
          Enter the API token. It is kept in this browser tab only (session storage) and is sent as
          a bearer token to the Control Plane.
        </p>
        <label htmlFor="token">API token</label>
        <input
          id="token"
          name="token"
          type="password"
          autoComplete="off"
          required
          value={token}
          onChange={(e) => {
            setToken(e.target.value);
          }}
        />
        {error ? (
          <p role="alert" className="alert alert-error">
            {error}
          </p>
        ) : null}
        <button type="submit" className="primary" disabled={busy || token.trim() === ''}>
          {busy ? 'Checking…' : 'Sign in'}
        </button>
      </form>
    </main>
  );
}
