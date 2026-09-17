import { Stack, Text, Title } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { LogsPanel } from '@/features/logs/components/LogsPanel';
import { useLogFilters } from '@/features/logs/useLogFilters';
import { useLogLevel } from '@/features/logs/useLogLevel';

export function LogsPage() {
  const { t } = useTranslation();
  const { service, component, setService, setComponent } = useLogFilters();
  const { level, setLevel } = useLogLevel();

  return (
    <Stack gap="lg">
      <Stack gap={4}>
        <Title order={1}>{t('logs.title')}</Title>
        <Text c="dimmed">{t('logs.description')}</Text>
      </Stack>

      <LogsPanel
        level={level}
        service={service}
        component={component}
        onLevelChange={setLevel}
        onServiceChange={setService}
        onComponentChange={setComponent}
      />
    </Stack>
  );
}
