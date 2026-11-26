import type {
  AdapterInfo,
  AuditEvent,
  ConnectionCreate,
  ConnectionHealth,
  ConnectionOut,
  ModuleSpec,
  PlatformInfo,
} from './types';

/** Error raised for every non-2xx answer; mirrors the API envelope {error:{code,message,details}}. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export interface ApiClientOptions {
  getToken: () => string | null;
  onUnauthorized?: () => void;
  fetchImpl?: typeof fetch;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = undefined;
  }
  if (isRecord(body) && isRecord(body['error'])) {
    const err = body['error'];
    const details = isRecord(err['details']) ? err['details'] : {};
    return new ApiError(
      response.status,
      typeof err['code'] === 'string' ? err['code'] : 'error',
      typeof err['message'] === 'string' ? err['message'] : response.statusText,
      details,
    );
  }
  return new ApiError(response.status, 'http_error', `HTTP ${response.status.toString()}`);
}

export function createApiClient({ getToken, onUnauthorized, fetchImpl }: ApiClientOptions) {
  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const init: RequestInit = { method, headers };
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(body);
    }
    let response: Response;
    try {
      response = await (fetchImpl ?? fetch)(path, init);
    } catch {
      throw new ApiError(0, 'network_error', 'Cannot reach the Control Plane API');
    }
    if (!response.ok) {
      const error = await toApiError(response);
      if (response.status === 401) onUnauthorized?.();
      throw error;
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
    platform: () => request<PlatformInfo>('GET', '/api/v1/platform'),
    modules: () => request<ModuleSpec[]>('GET', '/api/v1/modules'),
    adapters: () => request<AdapterInfo[]>('GET', '/api/v1/adapters'),
    connections: () => request<ConnectionOut[]>('GET', '/api/v1/connections'),
    createConnection: (body: ConnectionCreate) =>
      request<ConnectionOut>('POST', '/api/v1/connections', body),
    deleteConnection: (name: string) =>
      request<undefined>('DELETE', `/api/v1/connections/${encodeURIComponent(name)}`),
    connectionsHealth: () => request<ConnectionHealth[]>('GET', '/api/v1/health/connections'),
    auditEvents: (limit = 100) =>
      request<AuditEvent[]>('GET', `/api/v1/audit-events?limit=${limit.toString()}`),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
