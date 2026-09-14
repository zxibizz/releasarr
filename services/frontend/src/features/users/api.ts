import { apiRequest } from '@/lib/api/client';
import type { CreateUserPayload, UpdateUserPayload, User, UsersResponse } from '@/types';

export const usersApi = {
  list: (signal?: AbortSignal) => apiRequest<UsersResponse>('/users', { signal }),

  create: (payload: CreateUserPayload) =>
    apiRequest<User>('/users', { method: 'POST', body: payload }),

  update: (id: string, payload: UpdateUserPayload) =>
    apiRequest<User>(`/users/${encodeURIComponent(id)}`, { method: 'PATCH', body: payload }),

  remove: (id: string) =>
    apiRequest<void>(`/users/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
