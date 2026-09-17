import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { settingsApi } from '@/features/settings/api';
import { getErrorMessage } from '@/utils/errors';
import type {
  ConnectionTestPayload,
  SettingsIntegration,
  SettingsResponse,
  SettingsSection,
} from '@/types';

export const settingsKeys = {
  all: ['settings'] as const,
  detail: () => [...settingsKeys.all, 'detail'] as const,
};

export const settingsQuery = () => ({
  queryKey: settingsKeys.detail(),
  queryFn: ({ signal }: { signal: AbortSignal }) => settingsApi.get(signal),
});

export function useSettings() {
  return useQuery(settingsQuery());
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
