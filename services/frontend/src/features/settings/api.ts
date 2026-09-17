import { apiRequest } from '@/lib/api/client';
import type {
  ConnectionTestPayload,
  ConnectionTestResult,
  SettingsIntegration,
  SettingsResponse,
  SettingsSection,
} from '@/types';

export const settingsApi = {
  get: (signal?: AbortSignal) => apiRequest<SettingsResponse>('/settings', { signal }),

  updateSection: (section: SettingsSection, values: Record<string, unknown>) =>
    apiRequest<SettingsResponse>(`/settings/${section}`, {
      method: 'PATCH',
      body: { values },
    }),

  testConnection: (integration: SettingsIntegration, payload?: ConnectionTestPayload) =>
    apiRequest<ConnectionTestResult>(`/settings/test/${integration}`, {
      method: 'POST',
      ...(payload ? { body: payload } : {}),
    }),
};
