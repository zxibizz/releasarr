import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { settingsApi } from '@/features/settings/api';
import { getErrorMessage } from '@/utils/errors';
import type {
  ConnectionTestPayload,
  DownloadCategoriesResponse,
  IndexerCategoriesResponse,
  QualityProfilesResponse,
  SettingsIntegration,
  SettingsResponse,
  SettingsSection,
} from '@/types';

export const settingsKeys = {
  all: ['settings'] as const,
  detail: () => [...settingsKeys.all, 'detail'] as const,
  options: () => [...settingsKeys.all, 'options'] as const,
  qualityProfiles: (integration: string) =>
    [...settingsKeys.options(), 'quality-profiles', integration] as const,
  indexerCategories: () => [...settingsKeys.options(), 'indexer-categories'] as const,
  downloadCategories: () => [...settingsKeys.options(), 'download-categories'] as const,
};

export const settingsQuery = () => ({
  queryKey: settingsKeys.detail(),
  queryFn: ({ signal }: { signal: AbortSignal }) => settingsApi.get(signal),
});

export function useSettings() {
  return useQuery(settingsQuery());
}

/*
 * A lookup only reaches the service the modal is editing, and only while that
 * modal is open, so each is gated on `enabled` rather than fetched with the
 * settings. They are not retried: an unconfigured service fails the same way
 * every time, and the form says so instead of spinning.
 */
const optionQueryOptions = { enabled: true, retry: false, staleTime: 60_000 } as const;

export function useQualityProfiles(integration: 'sonarr' | 'radarr', enabled: boolean) {
  return useQuery({
    ...optionQueryOptions,
    enabled,
    queryKey: settingsKeys.qualityProfiles(integration),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      settingsApi.qualityProfiles(integration, signal),
    select: (data: QualityProfilesResponse) => data.profiles,
  });
}

export function useIndexerCategories(enabled: boolean) {
  return useQuery({
    ...optionQueryOptions,
    enabled,
    queryKey: settingsKeys.indexerCategories(),
    queryFn: ({ signal }: { signal: AbortSignal }) => settingsApi.indexerCategories(signal),
    select: (data: IndexerCategoriesResponse) => data.categories,
  });
}

export function useDownloadCategories(enabled: boolean) {
  return useQuery({
    ...optionQueryOptions,
    enabled,
    queryKey: settingsKeys.downloadCategories(),
    queryFn: ({ signal }: { signal: AbortSignal }) => settingsApi.downloadCategories(signal),
    select: (data: DownloadCategoriesResponse) => data.categories,
  });
}

export function useUpdateSettingsSection() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: ({ section, values }: { section: SettingsSection; values: Record<string, unknown> }) =>
      settingsApi.updateSection(section, values),
    onSuccess: (updated: SettingsResponse) => {
      queryClient.setQueryData(settingsKeys.detail(), updated);
      notifications.show({ message: t('settings.saved'), color: 'teal' });
    },
    onError: (error: unknown) => {
      notifications.show({
        title: t('settings.saveFailed'),
        message: getErrorMessage(error, ''),
        color: 'red',
      });
    },
  });
}

/**
 * Saves keys that belong to one subject but live in different sections, as a
 * service's credentials and its timeouts do.
 *
 * Sequential, not parallel: every PATCH answers with the whole settings
 * document, so concurrent writes would race and the slower reply would
 * overwrite the cache with pre-update values.
 */
export function useUpdateSettingsSections() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: async (changes: Partial<Record<SettingsSection, Record<string, unknown>>>) => {
      let latest: SettingsResponse | undefined;
      for (const [section, values] of Object.entries(changes)) {
        latest = await settingsApi.updateSection(section as SettingsSection, values);
      }
      return latest;
    },
    onSuccess: (updated: SettingsResponse | undefined) => {
      if (updated) {
        queryClient.setQueryData(settingsKeys.detail(), updated);
      }
      notifications.show({ message: t('settings.saved'), color: 'teal' });
    },
    onError: (error: unknown) => {
      notifications.show({
        title: t('settings.saveFailed'),
        message: getErrorMessage(error, ''),
        color: 'red',
      });
    },
  });
}

export function useTestConnection() {
  const { t } = useTranslation();
  return useMutation({
    mutationFn: ({
      integration,
      payload,
    }: {
      integration: SettingsIntegration;
      payload?: ConnectionTestPayload;
    }) => settingsApi.testConnection(integration, payload),
    onSuccess: (result) => {
      notifications.show({
        title: result.success ? t('settings.test.success') : t('settings.test.failed'),
        message: result.detail ?? undefined,
        color: result.success ? 'teal' : 'red',
      });
    },
    onError: (error: unknown) => {
      notifications.show({
        title: t('settings.test.failed'),
        message: getErrorMessage(error, ''),
        color: 'red',
      });
    },
  });
}
