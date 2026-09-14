import { apiRequest } from '@/lib/api/client';
import type {
  LoginPayload,
  LoginResponse,
  SessionUser,
  SetupPayload,
  SetupStatus,
} from '@/types';

export const authApi = {
  setupStatus: (signal?: AbortSignal) =>
    apiRequest<SetupStatus>('/auth/setup', { signal }),

  completeSetup: (payload: SetupPayload) =>
    apiRequest<LoginResponse>('/auth/setup', { method: 'POST', body: payload }),

  login: (payload: LoginPayload) =>
    apiRequest<LoginResponse>('/auth/login', { method: 'POST', body: payload }),

  refresh: () => apiRequest<LoginResponse>('/auth/refresh', { method: 'POST' }),

  logout: () => apiRequest<void>('/auth/logout', { method: 'POST' }),

  me: (signal?: AbortSignal) => apiRequest<SessionUser>('/auth/me', { signal }),
};
