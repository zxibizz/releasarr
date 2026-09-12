import { ActionIcon, Badge, Box, Code, Collapse, Group, Stack, Table, Text } from '@mantine/core';
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { formatLogContext } from '@/features/logs/context';
import { isTaskKind } from '@/features/tasks/formatting';
import type { RequestLogEntry } from '@/types';
import { formatDateTime } from '@/utils/formatters';
import { LOG_LEVEL_COLOR } from '@/utils/status';

/** The task is its own column, so repeating it in the context line adds nothing. */
const HIDDEN_METADATA_KEYS = ['task'];

const COLUMN_COUNT = 5;

export function TaskLogsTable({ entries }: { entries: RequestLogEntry[] }) {
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
            const context = formatLogContext(entry.metadata, HIDDEN_METADATA_KEYS);
            const hasDetails = Boolean(context || entry.stackTrace || entry.source);
            const task = entry.metadata?.task;

            return [
              <Table.Tr
                key={entry.id}
                onClick={() => hasDetails && toggle(entry.id)}
                style={{ cursor: hasDetails ? 'pointer' : 'default' }}
              >
                <Table.Td>
                  {hasDetails && (
                    <ActionIcon
                      variant="subtle"
                      color="gray"
                      aria-expanded={open}
                      aria-label={t('taskLogs.toggleDetails')}
                      onClick={(event) => {
                        event.stopPropagation();
                        toggle(entry.id);
                      }}
                    >
                      {open ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
                    </ActionIcon>
                  )}
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed" ff="monospace">
                    {formatDateTime(entry.occurredAt)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={LOG_LEVEL_COLOR[entry.level]} variant="light" size="sm">
                    {t(`logLevels.${entry.level}`)}
                  </Badge>
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
                  <Text size="sm" style={{ wordBreak: 'break-word' }}>
                    {entry.message}
                  </Text>
                </Table.Td>
              </Table.Tr>,

              <Table.Tr key={`${entry.id}-details`}>
                <Table.Td colSpan={COLUMN_COUNT} p={0} style={{ borderBottom: 'none' }}>
                  <Collapse expanded={open}>
                    <Box px="md" py="sm">
                      <Stack gap={6}>
                        {entry.source && (
                          <Group gap={6}>
                            <Text size="xs" c="dimmed">
                              {t('taskLogs.source')}:
                            </Text>
                            <Text size="xs" ff="monospace">
                              {entry.source}
                            </Text>
                          </Group>
                        )}
                        {context && (
                          <Text size="xs" c="dimmed" style={{ wordBreak: 'break-word' }}>
                            {t('requestLogsModal.context')}: {context}
                          </Text>
                        )}
                        {entry.stackTrace && <Code block>{entry.stackTrace}</Code>}
                      </Stack>
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
