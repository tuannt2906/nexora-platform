import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { createApiClient, type ApiClient } from './client';
import { clearToken, readToken, writeToken } from './token';

interface Session {
  token: string | null;
  api: ApiClient;
  /** Verifies the token against the API; throws ApiError when it is rejected. */
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({
  children,
  fetchImpl,
}: {
  children: ReactNode;
  fetchImpl?: typeof fetch;
}) {
  const [token, setToken] = useState<string | null>(() => readToken());
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 5_000 } } }),
  );

  const session = useMemo<Session>(() => {
    const logout = () => {
      clearToken();
      setToken(null);
      queryClient.clear();
    };
    const extra = fetchImpl ? { fetchImpl } : {};
    const api = createApiClient({ getToken: readToken, onUnauthorized: logout, ...extra });
    const login = async (candidate: string) => {
      const probe = createApiClient({ getToken: () => candidate, ...extra });
      await probe.platform(); // throws ApiError(401) for a wrong token
      writeToken(candidate);
      setToken(candidate);
    };
    return { token, api, login, logout };
  }, [token, queryClient, fetchImpl]);

  return (
    <QueryClientProvider client={queryClient}>
      <SessionContext.Provider value={session}>{children}</SessionContext.Provider>
    </QueryClientProvider>
  );
}

export function useSession(): Session {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used inside <SessionProvider>');
  return ctx;
}
