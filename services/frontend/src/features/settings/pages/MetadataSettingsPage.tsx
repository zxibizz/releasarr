import { Button, Card, Group, Stack, Text, Title } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { useTestConnection } from '@/features/settings/queries';
import { SettingsSectionForm } from '@/features/settings/components/SettingsSectionForm';
import type { SettingsIntegration } from '@/types';

const PROVIDERS: { key: SettingsIntegration; labelKey: string }[] = [
  { key: 'tvdb', labelKey: 'settings.metadata.tvdb' },
  { key: 'tmdb', labelKey: 'settings.metadata.tmdb' },
];

export function MetadataSettingsPage() {
  const { t } = useTranslation();
  const test = useTestConnection();

  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>{t('settings.metadata.title')}</Title>
        <Text c="dimmed" size="sm" mt={4}>
          {t('settings.metadata.description')}
        </Text>
      </div>

      <Card withBorder padding="md">
        <Text fw={600} mb="sm">
          {t('settings.services.testHeading')}
        </Text>
        <Stack gap="sm">
          {PROVIDERS.map((provider) => (
            <Group key={provider.key} justify="space-between" wrap="nowrap">
              <Text size="sm">{t(provider.labelKey)}</Text>
              <Button
                size="xs"
                variant="light"
                loading={test.isPending && test.variables?.integration === provider.key}
                onClick={() => test.mutate({ integration: provider.key })}
              >
                {t('settings.test.action')}
              </Button>
            </Group>
          ))}
        </Stack>
      </Card>

      <SettingsSectionForm section="metadata" titleKey="settings.metadata.formTitle" />
    </Stack>
  );
}
