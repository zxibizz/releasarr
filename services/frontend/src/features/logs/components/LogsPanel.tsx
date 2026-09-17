import { Alert, Button, Group, Loader, Select, Skeleton, Stack, Text } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { Panel } from '@/components/Panel';
import { LogsTable } from '@/features/logs/components/LogsTable';
import { componentsByGroup, isLogComponent } from '@/features/logs/components';
import { LOG_LEVELS, isLogLevel } from '@/features/logs/levels';
import { LOGS_PAGE_SIZE, useLogs } from '@/features/logs/queries';
import { LOG_SERVICES, isLogService } from '@/features/logs/services';
import type { LogComponent, LogService, RequestLogLevel } from '@/types';
import { getErrorMessage } from '@/utils/errors';

const ALL = 'all';

interface LogsPanelProps {
  level: RequestLogLevel | undefined;
  service: LogService | undefined;
  component: LogComponent | undefined;
  onLevelChange: (level: RequestLogLevel | undefined) => void;
  onServiceChange: (service: LogService | undefined) => void;
  onComponentChange: (component: LogComponent | undefined) => void;
}

/** The one log: every process's records, with whatever filters are set. */
export function LogsPanel({
  level,
  service,
  component,
  onLevelChange,
  onServiceChange,
  onComponentChange,
}: LogsPanelProps) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const logs = useLogs({ page, service, component, minLevel: level });

  const entries = logs.data?.logs ?? [];
  const total = logs.data?.total ?? 0;
  const lastPage = Math.max(1, Math.ceil(total / LOGS_PAGE_SIZE));

  const changeLevel = (value: string | null) => {
    onLevelChange(isLogLevel(value) ? value : undefined);
    // A page number from the previous filter rarely exists in the new result.
    setPage(1);
  };
  const changeService = (value: string | null) => {
    onServiceChange(isLogService(value) ? value : undefined);
    setPage(1);
  };
  const changeComponent = (value: string | null) => {
    onComponentChange(isLogComponent(value) ? value : undefined);
    setPage(1);
  };

  const componentGroups = componentsByGroup();

  return (
    <Stack gap="sm">
      <Group gap="sm" align="flex-end" wrap="wrap">
        <Select
          label={t('logs.levelFilterLabel')}
          value={level ?? ALL}
          onChange={changeLevel}
          allowDeselect={false}
          w={{ base: '100%', sm: 180 }}
          data={[
            { value: ALL, label: t('logs.allLevels') },
            ...LOG_LEVELS.map((value) => ({
              value,
              label: t(`logLevels.${value}`),
            })),
          ]}
        />
        <Select
          label={t('logs.serviceFilterLabel')}
          value={service ?? ALL}
          onChange={changeService}
          allowDeselect={false}
          w={{ base: '100%', sm: 180 }}
          data={[
            { value: ALL, label: t('logs.allServices') },
            ...LOG_SERVICES.map((value) => ({
              value,
              label: t(`logs.services.${value}`),
            })),
          ]}
        />
        <Select
          label={t('logs.componentFilterLabel')}
          value={component ?? ALL}
          onChange={changeComponent}
          allowDeselect={false}
          searchable
          w={{ base: '100%', sm: 240 }}
          data={[
            { value: ALL, label: t('logs.allComponents') },
            ...Object.entries(componentGroups).map(([group, components]) => ({
              group: t(`logs.componentGroups.${group}`),
              items: components.map((value) => ({ value, label: value })),
            })),
          ]}
        />
        <Group gap="sm" align="center">
          {logs.isFetching && <Loader size="xs" />}
          <Button
            size="sm"
            variant="default"
            leftSection={<IconRefresh size={16} />}
            onClick={() => void logs.refetch()}
          >
            {t('common.refresh')}
          </Button>
        </Group>
      </Group>

      {logs.error && (
        <Alert color="red" radius="lg" title={t('logs.error.title')}>
          <Stack align="flex-start" gap="sm">
            <Text>{getErrorMessage(logs.error, t('logs.error.description'))}</Text>
            <Button variant="light" size="xs" onClick={() => void logs.refetch()}>
              {t('common.tryAgain')}
            </Button>
          </Stack>
        </Alert>
      )}

      <Panel>
        {logs.isLoading ? (
          <Stack gap="sm" p="md">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} height={24} radius="sm" />
            ))}
          </Stack>
        ) : entries.length === 0 ? (
          <EmptyState
            icon="📋"
            title={t('logs.empty.title')}
            description={
              service || component || level
                ? t('logs.empty.filtered')
                : t('logs.empty.description')
            }
          />
        ) : (
          <LogsTable entries={entries} />
        )}
      </Panel>

      {total > 0 && (
        <Group justify="space-between" align="center">
          <Text size="sm" c="dimmed">
            {t('logs.pageStatus', { page, lastPage, total })}
          </Text>
          <Group gap="xs">
            <Button
              size="xs"
              variant="default"
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              {t('logs.previous')}
            </Button>
            <Button
              size="xs"
              variant="default"
              disabled={page >= lastPage}
              onClick={() => setPage((current) => current + 1)}
            >
              {t('logs.next')}
            </Button>
          </Group>
        </Group>
      )}
    </Stack>
  );
}
