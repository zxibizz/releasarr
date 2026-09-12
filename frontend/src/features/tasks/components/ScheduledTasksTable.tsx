import { ActionIcon, Group, Table, Text, Tooltip } from '@mantine/core';
import { IconPlayerPlay } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { StatusBadge } from '@/components/StatusBadge';
import { formatInterval, formatRelativeTime, formatRunDuration } from '@/features/tasks/formatting';
import { useRunTask } from '@/features/tasks/queries';
import type { ScheduledTask, SyncJobKind } from '@/types';
import { formatDateTime } from '@/utils/formatters';

interface ScheduledTasksTableProps {
  tasks: ScheduledTask[];
  /** Tasks with a queued or running job, so their run button shows progress. */
  activeKinds: Set<SyncJobKind>;
}

export function ScheduledTasksTable({ tasks, activeKinds }: ScheduledTasksTableProps) {
  const { t, i18n } = useTranslation();
  const runTask = useRunTask();

  return (
    <Table.ScrollContainer minWidth={720}>
      <Table highlightOnHover verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>{t('tasks.scheduled.columns.name')}</Table.Th>
            <Table.Th>{t('tasks.scheduled.columns.interval')}</Table.Th>
            <Table.Th>{t('tasks.scheduled.columns.lastExecution')}</Table.Th>
            <Table.Th>{t('tasks.scheduled.columns.lastDuration')}</Table.Th>
            <Table.Th>{t('tasks.scheduled.columns.nextExecution')}</Table.Th>
            <Table.Th w={60} />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {tasks.map((task) => {
            const pending = runTask.isPending && runTask.variables === task.kind;
            const duration = formatRunDuration(task.last_duration_ms);

            return (
              <Table.Tr key={task.kind}>
                <Table.Td>
                  <Group gap="xs" wrap="nowrap">
                    <Text fw={600} size="sm">
                      {t(`tasks.kinds.${task.kind}.name`)}
                    </Text>
                    {task.last_status === 'failed' && (
                      <Tooltip
                        label={task.last_error ?? t('tasks.scheduled.lastRunFailed')}
                        multiline
                        maw={320}
                      >
                        <StatusBadge status="failed" size="xs" />
                      </Tooltip>
                    )}
                  </Group>
                  <Text size="xs" c="dimmed">
                    {t(`tasks.kinds.${task.kind}.description`)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{formatInterval(task.interval_seconds)}</Text>
                </Table.Td>
                <Table.Td>
                  <Timestamp value={task.last_execution} locale={i18n.language} />
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c={duration ? undefined : 'dimmed'}>
                    {duration ?? '—'}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Timestamp
                    value={task.next_execution}
                    locale={i18n.language}
                    fallback={t('tasks.scheduled.pendingFirstRun')}
                  />
                </Table.Td>
                <Table.Td>
                  <Tooltip label={t('tasks.scheduled.runNow')}>
                    <ActionIcon
                      variant="subtle"
                      color="blue"
                      aria-label={t('tasks.scheduled.runTask', {
                        name: t(`tasks.kinds.${task.kind}.name`),
                      })}
                      loading={pending || activeKinds.has(task.kind)}
                      onClick={() => runTask.mutate(task.kind)}
                    >
                      <IconPlayerPlay size={16} />
                    </ActionIcon>
                  </Tooltip>
                </Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

function Timestamp({
  value,
  locale,
  fallback,
}: {
  value: string | null | undefined;
  locale: string;
  fallback?: string;
}) {
  const { t } = useTranslation();

  if (!value) {
    return (
      <Text size="sm" c="dimmed">
        {fallback ?? t('tasks.scheduled.never')}
      </Text>
    );
  }

  return (
    <Tooltip label={formatDateTime(value)}>
      <Text size="sm">{formatRelativeTime(value, locale)}</Text>
    </Tooltip>
  );
}
