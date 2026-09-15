import { apiRequest } from '@/lib/api/client';
import type { LoginPayload, LoginResponse, SessionUser, SetupPayload, SetupStatus } from '@/types';

export const authApi = {
  setupStatus: (signal?: AbortSignal) => apiRequest<SetupStatus>('/auth/setup', { signal }),

  completeSetup: (payload: SetupPayload) =>
    apiRequest<LoginResponse>('/auth/setup', { method: 'POST', body: payload }),

  login: (payload: LoginPayload) =>
    apiRequest<LoginResponse>('/auth/login', { method: 'POST', body: payload }),

  // No `refresh` here: restoring a session belongs to the API client, which
  // shares one in-flight rotation between the bootstrap and every 401 retry.
  logout: () => apiRequest<void>('/auth/logout', { method: 'POST' }),

  me: (signal?: AbortSignal) => apiRequest<SessionUser>('/auth/me', { signal }),
};
