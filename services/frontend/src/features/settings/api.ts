import { apiRequest } from '@/lib/api/client';
import type {
  ConnectionTestPayload,
  ConnectionTestResult,
  DownloadCategoriesResponse,
  IndexerCategoriesResponse,
  QualityProfilesResponse,
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

  qualityProfiles: (integration: 'sonarr' | 'radarr', signal?: AbortSignal) =>
    apiRequest<QualityProfilesResponse>(
      `/settings/options/quality-profiles/${integration}`,
      { signal },
    ),

  indexerCategories: (signal?: AbortSignal) =>
    apiRequest<IndexerCategoriesResponse>('/settings/options/indexer-categories', { signal }),

  downloadCategories: (signal?: AbortSignal) =>
    apiRequest<DownloadCategoriesResponse>('/settings/options/download-categories', { signal }),
};
