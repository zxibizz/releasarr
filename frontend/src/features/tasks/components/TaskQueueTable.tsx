import { ActionIcon, Badge, Box, Card, Collapse, Group, Stack, Table, Text } from '@mantine/core';
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { DataField } from '@/components/DataField';
import { StatusBadge } from '@/components/StatusBadge';
import { JobOutput } from '@/features/tasks/components/JobOutput';
import { formatRunDuration } from '@/features/tasks/formatting';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { SyncJob } from '@/types';
import { formatDateTime } from '@/utils/formatters';

const TRIGGER_COLORS: Record<string, string> = {
  api: 'blue',
  download_client: 'grape',
  schedule: 'gray',
};

const COLUMN_COUNT = 7;

/** Tracks which single run has its output revealed. */
function useExpandedJob() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const toggle = (jobId: string) => setExpanded((current) => (current === jobId ? null : jobId));

  return { expanded, toggle };
}

export function TaskQueueTable({ jobs }: { jobs: SyncJob[] }) {
  const isMobile = useIsMobile();

  return isMobile ? <TaskQueueCards jobs={jobs} /> : <TaskQueueGrid jobs={jobs} />;
}

function TaskQueueGrid({ jobs }: { jobs: SyncJob[] }) {
  const { t } = useTranslation();
  const { expanded, toggle } = useExpandedJob();

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
                  <ExpandToggle open={open} name={name} onToggle={() => toggle(job.id)} />
                </Table.Td>
                <Table.Td>
                  <Text size="sm" fw={600}>
                    {name}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <TriggerBadge job={job} />
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

function TaskQueueCards({ jobs }: { jobs: SyncJob[] }) {
  const { t } = useTranslation();
  const { expanded, toggle } = useExpandedJob();

  return (
    <Stack gap="xs" p="xs">
      {jobs.map((job) => {
        const open = expanded === job.id;
        const duration = formatRunDuration(job.duration_ms);
        const name = t(`tasks.kinds.${job.kind}.name`);

        return (
          <Card key={job.id} withBorder radius="md" padding="sm">
            <Stack gap="xs">
              <Group justify="space-between" align="center" wrap="nowrap" gap="sm">
                <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                  <ExpandToggle open={open} name={name} onToggle={() => toggle(job.id)} />
                  <Text size="sm" fw={600} style={{ minWidth: 0 }}>
                    {name}
                  </Text>
                </Group>
                <StatusBadge status={job.status} size="sm" />
              </Group>

              <Stack gap={4}>
                <DataField label={t('tasks.queue.columns.trigger')}>
                  <TriggerBadge job={job} />
                </DataField>
                <DataField label={t('tasks.queue.columns.queued')}>
                  <Text size="sm">{formatDateTime(job.queued_at)}</Text>
                </DataField>
                <DataField label={t('tasks.queue.columns.started')}>
                  <Text size="sm" c={job.started_at ? undefined : 'dimmed'}>
                    {job.started_at ? formatDateTime(job.started_at) : '—'}
                  </Text>
                </DataField>
                <DataField label={t('tasks.queue.columns.duration')}>
                  <Text size="sm" c={duration ? undefined : 'dimmed'}>
                    {duration ?? '—'}
                  </Text>
                </DataField>
              </Stack>

              <Collapse expanded={open}>
                <Box pt="xs">
                  <JobOutput result={job.result} error={job.error} />
                </Box>
              </Collapse>
            </Stack>
          </Card>
        );
      })}
    </Stack>
  );
}

function TriggerBadge({ job }: { job: SyncJob }) {
  const { t } = useTranslation();

  return (
    <Badge size="sm" variant="light" color={TRIGGER_COLORS[job.trigger] ?? 'gray'}>
      {t(`tasks.triggers.${job.trigger}`)}
    </Badge>
  );
}

function ExpandToggle({
  open,
  name,
  onToggle,
}: {
  open: boolean;
  name: string;
  onToggle: () => void;
}) {
  const { t } = useTranslation();

  return (
    <ActionIcon
      variant="subtle"
      color="gray"
      aria-expanded={open}
      aria-label={t('tasks.queue.toggleDetails', { name })}
      onClick={(event) => {
        event.stopPropagation();
        onToggle();
      }}
    >
      {open ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
    </ActionIcon>
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
