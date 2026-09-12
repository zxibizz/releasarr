import {
  ActionIcon,
  Badge,
  Box,
  Card,
  Code,
  Collapse,
  Group,
  Stack,
  Table,
  Text,
} from '@mantine/core';
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { formatLogContext } from '@/features/logs/context';
import { isTaskKind } from '@/features/tasks/formatting';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { RequestLogEntry } from '@/types';
import { formatDateTime } from '@/utils/formatters';
import { LOG_LEVEL_COLOR } from '@/utils/status';

/** The task is its own column, so repeating it in the context line adds nothing. */
const HIDDEN_METADATA_KEYS = ['task'];

const COLUMN_COUNT = 5;

interface EntryView {
  context: string | null;
  hasDetails: boolean;
  task: unknown;
}

const describe = (entry: RequestLogEntry): EntryView => {
  const context = formatLogContext(entry.metadata, HIDDEN_METADATA_KEYS);

  return {
    context,
    hasDetails: Boolean(context || entry.stackTrace || entry.source),
    task: entry.metadata?.task,
  };
};

export function TaskLogsTable({ entries }: { entries: RequestLogEntry[] }) {
  const isMobile = useIsMobile();

  return isMobile ? <TaskLogsCards entries={entries} /> : <TaskLogsGrid entries={entries} />;
}

function TaskLogsGrid({ entries }: { entries: RequestLogEntry[] }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<string | null>(null);

  const toggle = (id: string) => setExpanded((current) => (current === id ? null : id));

  return (
    <Table.ScrollContainer minWidth={760}>
      <Table verticalSpacing="xs" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={44} />
            <Table.Th w={180}>{t('taskLogs.columns.time')}</Table.Th>
            <Table.Th w={100}>{t('taskLogs.columns.level')}</Table.Th>
            <Table.Th w={170}>{t('taskLogs.columns.task')}</Table.Th>
            <Table.Th>{t('taskLogs.columns.message')}</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {entries.map((entry) => {
            const open = expanded === entry.id;
            const { context, hasDetails, task } = describe(entry);

            return [
              <Table.Tr
                key={entry.id}
                onClick={() => hasDetails && toggle(entry.id)}
                style={{ cursor: hasDetails ? 'pointer' : 'default' }}
              >
                <Table.Td>
                  {hasDetails && <ExpandToggle open={open} onToggle={() => toggle(entry.id)} />}
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed" ff="monospace">
                    {formatDateTime(entry.occurredAt)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <LevelBadge entry={entry} />
                </Table.Td>
                <Table.Td>
                  {isTaskKind(task) ? (
                    <Text size="sm">{t(`tasks.kinds.${task}.name`)}</Text>
                  ) : (
                    <Text size="sm" c="dimmed">
                      —
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>
                  <Text size="sm" className="break-anywhere">
                    {entry.message}
                  </Text>
                </Table.Td>
              </Table.Tr>,

              <Table.Tr key={`${entry.id}-details`}>
                <Table.Td colSpan={COLUMN_COUNT} p={0} style={{ borderBottom: 'none' }}>
                  <Collapse expanded={open}>
                    <Box px="md" py="sm">
                      <EntryDetails entry={entry} context={context} />
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

function TaskLogsCards({ entries }: { entries: RequestLogEntry[] }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<string | null>(null);

  const toggle = (id: string) => setExpanded((current) => (current === id ? null : id));

  return (
    <Stack gap="xs" p="xs">
      {entries.map((entry) => {
        const open = expanded === entry.id;
        const { context, hasDetails, task } = describe(entry);

        return (
          <Card key={entry.id} withBorder radius="md" padding="sm">
            <Stack gap="xs">
              <Group justify="space-between" align="center" wrap="nowrap" gap="xs">
                <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                  <LevelBadge entry={entry} />
                  <Text size="xs" c="dimmed" ff="monospace" style={{ minWidth: 0 }}>
                    {formatDateTime(entry.occurredAt)}
                  </Text>
                </Group>
                {hasDetails && <ExpandToggle open={open} onToggle={() => toggle(entry.id)} />}
              </Group>

              {isTaskKind(task) && (
                <Text size="xs" c="dimmed">
                  {t('taskLogs.columns.task')}: {t(`tasks.kinds.${task}.name`)}
                </Text>
              )}

              <Text size="sm" className="break-anywhere">
                {entry.message}
              </Text>

              <Collapse expanded={open}>
                <Box pt={4}>
                  <EntryDetails entry={entry} context={context} />
                </Box>
              </Collapse>
            </Stack>
          </Card>
        );
      })}
    </Stack>
  );
}

function LevelBadge({ entry }: { entry: RequestLogEntry }) {
  const { t } = useTranslation();

  return (
    <Badge color={LOG_LEVEL_COLOR[entry.level]} variant="light" size="sm">
      {t(`logLevels.${entry.level}`)}
    </Badge>
  );
}

function ExpandToggle({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  const { t } = useTranslation();

  return (
    <ActionIcon
      variant="subtle"
      color="gray"
      aria-expanded={open}
      aria-label={t('taskLogs.toggleDetails')}
      onClick={(event) => {
        event.stopPropagation();
        onToggle();
      }}
    >
      {open ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
    </ActionIcon>
  );
}

function EntryDetails({ entry, context }: { entry: RequestLogEntry; context: string | null }) {
  const { t } = useTranslation();

  return (
    <Stack gap={6}>
      {entry.source && (
        <Group gap={6} wrap="wrap">
          <Text size="xs" c="dimmed">
            {t('taskLogs.source')}:
          </Text>
          <Text size="xs" ff="monospace" className="break-anywhere">
            {entry.source}
          </Text>
        </Group>
      )}
      {context && (
        <Text size="xs" c="dimmed" className="break-anywhere">
          {t('requestLogsModal.context')}: {context}
        </Text>
      )}
      {entry.stackTrace && (
        <Code block className="break-anywhere">
          {entry.stackTrace}
        </Code>
      )}
    </Stack>
  );
}
