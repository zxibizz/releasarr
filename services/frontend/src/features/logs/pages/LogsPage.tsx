import { Stack, Tabs, Text, Title } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { LogsPanel } from '@/features/logs/components/LogsPanel';
import { LOG_SERVICES, isLogService } from '@/features/logs/services';
import { useLogFilters } from '@/features/logs/useLogFilters';
import { useLogLevel } from '@/features/logs/useLogLevel';

export function LogsPage() {
  const { t } = useTranslation();
  const { service, task, setService, setTask } = useLogFilters();
  const { level, setLevel } = useLogLevel();

  return (
    <Stack gap="lg">
      <Stack gap={4}>
        <Title order={1}>{t('taskLogs.title')}</Title>
        <Text c="dimmed">{t('taskLogs.description')}</Text>
      </Stack>

      <Tabs
        value={service}
        onChange={(value) => {
          if (isLogService(value)) setService(value);
        }}
      >
        <Tabs.List>
          {LOG_SERVICES.map((value) => (
            <Tabs.Tab key={value} value={value}>
              {t(`taskLogs.tabs.${value}`)}
            </Tabs.Tab>
          ))}
        </Tabs.List>

        {LOG_SERVICES.map((value) => (
          <Tabs.Panel key={value} value={value} pt="md">
            {/*
              Both panels stay mounted and only the selected one is shown, so
              each has to be told whether it is that one: otherwise the hidden
              tab keeps querying and its interval polls the same file twice.
            */}
            <LogsPanel
              service={value}
              level={level}
              task={task}
              onLevelChange={setLevel}
              onTaskChange={setTask}
              active={service === value}
            />
          </Tabs.Panel>
        ))}
      </Tabs>
    </Stack>
  );
}
