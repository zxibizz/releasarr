import { Button, Card, Group, Stack, Text, Title } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { useTestConnection } from '@/features/settings/queries';
import { SettingsSectionForm } from '@/features/settings/components/SettingsSectionForm';
import type { SettingsIntegration } from '@/types';

const INTEGRATIONS: { key: SettingsIntegration; labelKey: string }[] = [
  { key: 'sonarr', labelKey: 'settings.services.sonarr' },
  { key: 'radarr', labelKey: 'settings.services.radarr' },
  { key: 'prowlarr', labelKey: 'settings.services.prowlarr' },
  { key: 'qbittorrent', labelKey: 'settings.services.qbittorrent' },
];

export function ServicesSettingsPage() {
  const { t } = useTranslation();
  const test = useTestConnection();

  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>{t('settings.services.title')}</Title>
        <Text c="dimmed" size="sm" mt={4}>
          {t('settings.services.description')}
        </Text>
      </div>

      <Card withBorder padding="md">
        <Group justify="space-between" wrap="nowrap" mb="sm">
          <Text fw={600}>{t('settings.services.testHeading')}</Text>
        </Group>
        <Stack gap="sm">
          {INTEGRATIONS.map((integration) => (
            <Group key={integration.key} justify="space-between" wrap="nowrap">
              <Text size="sm">{t(integration.labelKey)}</Text>
              <Button
                size="xs"
                variant="light"
                loading={test.isPending && test.variables?.integration === integration.key}
                onClick={() => test.mutate({ integration: integration.key })}
              >
                {t('settings.test.action')}
              </Button>
            </Group>
          ))}
        </Stack>
      </Card>

      <SettingsSectionForm section="services" titleKey="settings.services.formTitle" />
    </Stack>
  );
}
