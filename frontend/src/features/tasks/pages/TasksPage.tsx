import { Alert, Button, Group, Loader, Paper, Skeleton, Stack, Text, Title } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { ScheduledTasksTable } from '@/features/tasks/components/ScheduledTasksTable';
import { TaskLogsSection } from '@/features/tasks/components/TaskLogsSection';
import { QueueSummary, TaskQueueTable } from '@/features/tasks/components/TaskQueueTable';
import {
  JOB_HISTORY_LIMIT,
  isActiveJob,
  isStalledJob,
  useScheduledTasks,
  useSyncJobs,
  useTriggerFullSync,
} from '@/features/tasks/queries';
import type { SyncJobKind } from '@/types';
import { getErrorMessage } from '@/utils/errors';

export function TasksPage() {
  const { t } = useTranslation();
  const scheduled = useScheduledTasks();
  const jobs = useSyncJobs(JOB_HISTORY_LIMIT);
  const triggerFullSync = useTriggerFullSync();

  const jobList = jobs.data ?? [];

  const activeKinds = useMemo(
    () => new Set<SyncJobKind>((jobs.data ?? []).filter(isActiveJob).map((job) => job.kind)),
    [jobs.data],
  );

  const stalled = jobList.some((job) => isActiveJob(job) && isStalledJob(job));
  const error = scheduled.error ?? jobs.error;

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <Stack gap={4}>
          <Title order={1}>{t('tasks.page.title')}</Title>
          <Text c="dimmed">{t('tasks.page.subtitle')}</Text>
        </Stack>

        <Group gap="sm">
          {(scheduled.isFetching || jobs.isFetching) && <Loader size="xs" />}
          <Button
            size="sm"
            variant="light"
            leftSection={<IconRefresh size={16} />}
            loading={triggerFullSync.isPending}
            onClick={() => triggerFullSync.mutate()}
          >
            {t('tasks.page.runAll')}
          </Button>
        </Group>
      </Group>

      {error && (
        <Alert color="red" radius="lg" title={t('tasks.page.error.title')}>
          <Stack align="flex-start" gap="sm">
            <Text>{getErrorMessage(error, t('tasks.page.error.description'))}</Text>
            <Button
              variant="light"
              size="xs"
              onClick={() => {
                void scheduled.refetch();
                void jobs.refetch();
              }}
            >
              {t('common.tryAgain')}
            </Button>
          </Stack>
        </Alert>
      )}

      {stalled && (
        <Alert color="yellow" radius="lg" title={t('tasks.page.stalled.title')}>
          {t('tasks.page.stalled.description')}
        </Alert>
      )}

      <Stack gap="sm">
        <Title order={3}>{t('tasks.scheduled.title')}</Title>
        <Paper withBorder radius="lg" p={0}>
          {scheduled.isLoading ? (
            <TableSkeleton rows={4} />
          ) : (
            <ScheduledTasksTable tasks={scheduled.data ?? []} activeKinds={activeKinds} />
          )}
        </Paper>
      </Stack>

      <Stack gap="sm">
        <Group justify="space-between" align="center">
          <Title order={3}>{t('tasks.queue.title')}</Title>
          <QueueSummary jobs={jobList} />
        </Group>
        <Text size="sm" c="dimmed">
          {t('tasks.queue.description')}
        </Text>
        <Paper withBorder radius="lg" p={0}>
          {jobs.isLoading ? (
            <TableSkeleton rows={3} />
          ) : jobList.length === 0 ? (
            <EmptyState
              icon="🗒️"
              title={t('tasks.queue.empty.title')}
              description={t('tasks.queue.empty.description')}
            />
          ) : (
            <TaskQueueTable jobs={jobList} />
          )}
        </Paper>
      </Stack>

      <TaskLogsSection />
    </Stack>
  );
}

function TableSkeleton({ rows }: { rows: number }) {
  return (
    <Stack gap="sm" p="md">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} height={32} radius="sm" />
      ))}
    </Stack>
  );
}
