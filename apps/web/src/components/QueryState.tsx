import type { UseQueryResult } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ApiError } from '../api/client';

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.code === 'network_error' ? error.message : `${error.message} (${error.code})`;
  }
  return error instanceof Error ? error.message : 'Unexpected error';
}

/** Renders loading / error states uniformly; calls `children` once data is available. */
export function QueryState<T>({
  query,
  children,
}: {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
}) {
  if (query.isPending) {
    return (
      <p role="status" className="muted">
        Loading…
      </p>
    );
  }
  if (query.isError) {
    return (
      <div role="alert" className="alert alert-error">
        <strong>Request failed.</strong> {errorMessage(query.error)}{' '}
        <button type="button" onClick={() => void query.refetch()}>
          Retry
        </button>
      </div>
    );
  }
  return <>{children(query.data)}</>;
}
