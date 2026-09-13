import { Alert, Button, Group, Loader, Select, Skeleton, Stack, Text } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { Panel } from '@/components/Panel';
import { LogsTable } from '@/features/logs/components/LogsTable';
import { LOGS_PAGE_SIZE, useLogs } from '@/features/logs/queries';
import { TASK_KINDS, isTaskKind } from '@/features/tasks/formatting';
import type { LogService, SyncJobKind } from '@/types';
import { getErrorMessage } from '@/utils/errors';

const ALL_TASKS = 'all';

interface LogsPanelProps {
  service: LogService;
  task: SyncJobKind | undefined;
  onTaskChange: (task: SyncJobKind | undefined) => void;
  /** False while the other process's tab is the one being shown. */
  active: boolean;
}

/** One process's log: its own page, its own task filter, its own refresh. */
export function LogsPanel({ service, task, onTaskChange, active }: LogsPanelProps) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const logs = useLogs({ page, service, task, active });

  const entries = logs.data?.logs ?? [];
  const total = logs.data?.total ?? 0;
  const lastPage = Math.max(1, Math.ceil(total / LOGS_PAGE_SIZE));

  // Only work done inside a background task is logged with `task` bound onto it,
  // and that work runs in the scheduler, so the filter would find nothing here.
  const hasTaskFilter = service === 'scheduler';

  const changeTask = (value: string | null) => {
    onTaskChange(isTaskKind(value) ? value : undefined);
    // A page number from the previous filter rarely exists in the new result.
    setPage(1);
  };

  return (
    <Stack gap="sm">
      <Group gap="sm" align="flex-end" wrap="wrap">
        {hasTaskFilter && (
          <Select
            label={t('taskLogs.filterLabel')}
            value={task ?? ALL_TASKS}
            onChange={changeTask}
            allowDeselect={false}
            w={{ base: '100%', sm: 220 }}
            data={[
              { value: ALL_TASKS, label: t('taskLogs.allTasks') },
              ...TASK_KINDS.map((kind) => ({
                value: kind,
                label: t(`tasks.kinds.${kind}.name`),
              })),
            ]}
          />
        )}
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
        <Alert color="red" radius="lg" title={t('taskLogs.error.title')}>
          <Stack align="flex-start" gap="sm">
            <Text>{getErrorMessage(logs.error, t('taskLogs.error.description'))}</Text>
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
            title={t('taskLogs.empty.title')}
            description={
              task
                ? t('taskLogs.empty.filtered', { name: t(`tasks.kinds.${task}.name`) })
                : t('taskLogs.empty.description')
            }
          />
        ) : (
          <LogsTable entries={entries} />
        )}
      </Panel>

      {total > 0 && (
        <Group justify="space-between" align="center">
          <Text size="sm" c="dimmed">
            {t('taskLogs.pageStatus', { page, lastPage, total })}
          </Text>
          <Group gap="xs">
            <Button
              size="xs"
              variant="default"
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              {t('taskLogs.previous')}
            </Button>
            <Button
              size="xs"
              variant="default"
              disabled={page >= lastPage}
              onClick={() => setPage((current) => current + 1)}
            >
              {t('taskLogs.next')}
            </Button>
          </Group>
        </Group>
      )}
    </Stack>
  );
}
