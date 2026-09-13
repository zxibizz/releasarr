import { ActionIcon, Card, Group, Stack, Table, Text, Tooltip } from '@mantine/core';
import { IconPlayerPlay } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { DataField } from '@/components/DataField';
import { StatusBadge } from '@/components/StatusBadge';
import { formatInterval, formatRelativeTime, formatRunDuration } from '@/features/tasks/formatting';
import { useRunTask } from '@/features/tasks/queries';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { ScheduledTask, SyncJobKind } from '@/types';
import { formatDateTime } from '@/utils/formatters';

interface ScheduledTasksTableProps {
  tasks: ScheduledTask[];
  /** Tasks with a queued or running job, so their run button shows progress. */
  activeKinds: Set<SyncJobKind>;
}

export function ScheduledTasksTable({ tasks, activeKinds }: ScheduledTasksTableProps) {
  const isMobile = useIsMobile();

  return isMobile ? (
    <ScheduledTasksCards tasks={tasks} activeKinds={activeKinds} />
  ) : (
    <ScheduledTasksGrid tasks={tasks} activeKinds={activeKinds} />
  );
}

function ScheduledTasksGrid({ tasks, activeKinds }: ScheduledTasksTableProps) {
  const { t, i18n } = useTranslation();

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
            const duration = formatRunDuration(task.last_duration_ms);

            return (
              <Table.Tr key={task.kind}>
                <Table.Td>
                  <Group gap="xs" wrap="nowrap">
                    <Text fw={600} size="sm">
                      {t(`tasks.kinds.${task.kind}.name`)}
                    </Text>
                    <FailureBadge task={task} />
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
                  <RunButton task={task} activeKinds={activeKinds} />
                </Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

function ScheduledTasksCards({ tasks, activeKinds }: ScheduledTasksTableProps) {
  const { t, i18n } = useTranslation();

  return (
    <Stack gap="xs" p="xs">
      {tasks.map((task) => {
        const duration = formatRunDuration(task.last_duration_ms);

        return (
          <Card key={task.kind} withBorder radius="md" padding="sm">
            <Stack gap="xs">
              <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
                <Stack gap={2} style={{ minWidth: 0 }}>
                  <Group gap="xs" wrap="nowrap">
                    <Text fw={600} size="sm">
                      {t(`tasks.kinds.${task.kind}.name`)}
                    </Text>
                    <FailureBadge task={task} />
                  </Group>
                  <Text size="xs" c="dimmed">
                    {t(`tasks.kinds.${task.kind}.description`)}
                  </Text>
                </Stack>
                <RunButton task={task} activeKinds={activeKinds} />
              </Group>

              <Stack gap={4}>
                <DataField label={t('tasks.scheduled.columns.interval')}>
                  <Text size="sm">{formatInterval(task.interval_seconds)}</Text>
                </DataField>
                <DataField label={t('tasks.scheduled.columns.lastExecution')}>
                  <Timestamp value={task.last_execution} locale={i18n.language} />
                </DataField>
                <DataField label={t('tasks.scheduled.columns.lastDuration')}>
                  <Text size="sm" c={duration ? undefined : 'dimmed'}>
                    {duration ?? '—'}
                  </Text>
                </DataField>
                <DataField label={t('tasks.scheduled.columns.nextExecution')}>
                  <Timestamp
                    value={task.next_execution}
                    locale={i18n.language}
                    fallback={t('tasks.scheduled.pendingFirstRun')}
                  />
                </DataField>
              </Stack>
            </Stack>
          </Card>
        );
      })}
    </Stack>
  );
}

function FailureBadge({ task }: { task: ScheduledTask }) {
  const { t } = useTranslation();

  if (task.last_status !== 'failed') {
    return null;
  }

  return (
    <Tooltip label={task.last_error ?? t('tasks.scheduled.lastRunFailed')} multiline maw={320}>
      <StatusBadge status="failed" size="xs" />
    </Tooltip>
  );
}

function RunButton({ task, activeKinds }: { task: ScheduledTask; activeKinds: Set<SyncJobKind> }) {
  const { t } = useTranslation();
  const runTask = useRunTask();

  return (
    <Tooltip label={t('tasks.scheduled.runNow')}>
      <ActionIcon
        variant="subtle"
        color="blue"
        aria-label={t('tasks.scheduled.runTask', {
          name: t(`tasks.kinds.${task.kind}.name`),
        })}
        loading={runTask.isPending || activeKinds.has(task.kind)}
        onClick={() => runTask.mutate(task.kind)}
      >
        <IconPlayerPlay size={16} />
      </ActionIcon>
    </Tooltip>
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
