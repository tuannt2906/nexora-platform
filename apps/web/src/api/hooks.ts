import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSession } from './context';
import type { ConnectionCreate } from './types';

export function usePlatform() {
  const { api } = useSession();
  return useQuery({ queryKey: ['platform'], queryFn: api.platform });
}
export function useModules() {
  const { api } = useSession();
  return useQuery({ queryKey: ['modules'], queryFn: api.modules });
}
export function useAdapters() {
  const { api } = useSession();
  return useQuery({ queryKey: ['adapters'], queryFn: api.adapters });
}
export function useConnections() {
  const { api } = useSession();
  return useQuery({ queryKey: ['connections'], queryFn: api.connections });
}
export function useConnectionsHealth() {
  const { api } = useSession();
  return useQuery({ queryKey: ['connections-health'], queryFn: api.connectionsHealth });
}
export function useAuditEvents() {
  const { api } = useSession();
  return useQuery({ queryKey: ['audit'], queryFn: () => api.auditEvents() });
}

export function useCreateConnection() {
  const { api } = useSession();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ConnectionCreate) => api.createConnection(body),
    onSuccess: () => qc.invalidateQueries(),
  });
}
export function useDeleteConnection() {
  const { api } = useSession();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.deleteConnection(name),
    onSuccess: () => qc.invalidateQueries(),
  });
}
