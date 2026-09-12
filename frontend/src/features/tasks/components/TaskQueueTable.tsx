import { ActionIcon, Badge, Box, Collapse, Group, Table, Text } from '@mantine/core';
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { StatusBadge } from '@/components/StatusBadge';
import { JobOutput } from '@/features/tasks/components/JobOutput';
import { formatRunDuration } from '@/features/tasks/formatting';
import type { SyncJob } from '@/types';
import { formatDateTime } from '@/utils/formatters';

const TRIGGER_COLORS: Record<string, string> = {
  api: 'blue',
  download_client: 'grape',
  schedule: 'gray',
};

const COLUMN_COUNT = 7;

export function TaskQueueTable({ jobs }: { jobs: SyncJob[] }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<string | null>(null);

  const toggle = (jobId: string) => setExpanded((current) => (current === jobId ? null : jobId));

  return (
    <Table.ScrollContainer minWidth={760}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={44} />
            <Table.Th>{t('tasks.queue.columns.name')}</Table.Th>
            <Table.Th>{t('tasks.queue.columns.trigger')}</Table.Th>
            <Table.Th>{t('tasks.queue.columns.queued')}</Table.Th>
            <Table.Th>{t('tasks.queue.columns.started')}</Table.Th>
            <Table.Th>{t('tasks.queue.columns.duration')}</Table.Th>
            <Table.Th>{t('tasks.queue.columns.status')}</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {jobs.map((job) => {
            const open = expanded === job.id;
            const duration = formatRunDuration(job.duration_ms);
            const name = t(`tasks.kinds.${job.kind}.name`);

            return [
              <Table.Tr key={job.id} onClick={() => toggle(job.id)} style={{ cursor: 'pointer' }}>
                <Table.Td>
                  <ActionIcon
                    variant="subtle"
                    color="gray"
                    aria-expanded={open}
                    aria-label={t('tasks.queue.toggleDetails', { name })}
                    onClick={(event) => {
                      event.stopPropagation();
                      toggle(job.id);
                    }}
                  >
                    {open ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
                  </ActionIcon>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" fw={600}>
                    {name}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge size="sm" variant="light" color={TRIGGER_COLORS[job.trigger] ?? 'gray'}>
                    {t(`tasks.triggers.${job.trigger}`)}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{formatDateTime(job.queued_at)}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c={job.started_at ? undefined : 'dimmed'}>
                    {job.started_at ? formatDateTime(job.started_at) : '—'}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c={duration ? undefined : 'dimmed'}>
                    {duration ?? '—'}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <StatusBadge status={job.status} size="sm" />
                </Table.Td>
              </Table.Tr>,

              <Table.Tr key={`${job.id}-details`}>
                <Table.Td colSpan={COLUMN_COUNT} p={0} style={{ borderBottom: 'none' }}>
                  <Collapse expanded={open}>
                    <Box px="md" py="sm">
                      <JobOutput result={job.result} error={job.error} />
                    </Box>
                  </Collapse>
                </Table.Td>
              </Table.Tr>,
            ];
          })}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

export function QueueSummary({ jobs }: { jobs: SyncJob[] }) {
  const { t } = useTranslation();
  const active = jobs.filter((job) => job.status === 'queued' || job.status === 'running').length;

  return (
    <Group gap="xs">
      <Text size="sm" c="dimmed">
        {t('tasks.queue.count', { count: jobs.length })}
      </Text>
      {active > 0 && (
        <Badge size="sm" variant="light" color="blue">
          {t('tasks.queue.active', { count: active })}
        </Badge>
      )}
    </Group>
  );
}
