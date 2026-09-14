import { apiRequest } from '@/lib/api/client';
import type {
  CreateServiceKeyPayload,
  CreateUserPayload,
  ServiceApiKeyCreated,
  ServiceApiKeysResponse,
  UpdateUserPayload,
  User,
  UsersResponse,
} from '@/types';

export const usersApi = {
  list: (signal?: AbortSignal) => apiRequest<UsersResponse>('/users', { signal }),

  create: (payload: CreateUserPayload) =>
    apiRequest<User>('/users', { method: 'POST', body: payload }),

  update: (id: string, payload: UpdateUserPayload) =>
    apiRequest<User>(`/users/${encodeURIComponent(id)}`, { method: 'PATCH', body: payload }),

  remove: (id: string) =>
    apiRequest<void>(`/users/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};

export const serviceKeysApi = {
  list: (signal?: AbortSignal) =>
    apiRequest<ServiceApiKeysResponse>('/service-keys', { signal }),

  create: (payload: CreateServiceKeyPayload) =>
    apiRequest<ServiceApiKeyCreated>('/service-keys', { method: 'POST', body: payload }),

  revoke: (id: string) =>
    apiRequest<void>(`/service-keys/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
