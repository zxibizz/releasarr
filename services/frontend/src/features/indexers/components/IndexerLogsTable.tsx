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

import { useIsMobile } from '@/hooks/useIsMobile';
import type { IndexerLogEntry } from '@/types';
import { formatDateTime } from '@/utils/formatters';
import { INDEXER_LOG_LEVEL_COLOR } from '@/utils/status';

const COLUMN_COUNT = 5;

/** Only the exception is hidden; Prowlarr's messages are already one line each. */
const hasDetails = (entry: IndexerLogEntry) => Boolean(entry.exception || entry.method);

export function IndexerLogsTable({ entries }: { entries: IndexerLogEntry[] }) {
  const isMobile = useIsMobile();

  return isMobile ? <LogsCards entries={entries} /> : <LogsGrid entries={entries} />;
}

function LogsGrid({ entries }: { entries: IndexerLogEntry[] }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<number | null>(null);

  const toggle = (id: number) => setExpanded((current) => (current === id ? null : id));

  return (
    <Table.ScrollContainer minWidth={720}>
      <Table verticalSpacing="xs" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={44} />
            <Table.Th w={150}>{t('indexers.logs.columns.time')}</Table.Th>
            <Table.Th w={100}>{t('indexers.logs.columns.level')}</Table.Th>
            <Table.Th w={180}>{t('indexers.logs.columns.component')}</Table.Th>
            <Table.Th>{t('indexers.logs.columns.message')}</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {entries.map((entry) => {
            const open = expanded === entry.id;
            const expandable = hasDetails(entry);

            return [
              <Table.Tr
                key={entry.id}
                onClick={() => expandable && toggle(entry.id)}
                style={{ cursor: expandable ? 'pointer' : 'default' }}
              >
                <Table.Td>
                  {expandable && <ExpandToggle open={open} onToggle={() => toggle(entry.id)} />}
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed" ff="monospace">
                    {formatDateTime(entry.occurred_at)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <LevelBadge entry={entry} />
                </Table.Td>
                <Table.Td>
                  <Component entry={entry} />
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
                      <EntryDetails entry={entry} />
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

function LogsCards({ entries }: { entries: IndexerLogEntry[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  const toggle = (id: number) => setExpanded((current) => (current === id ? null : id));

  return (
    <Stack gap="xs">
      {entries.map((entry) => {
        const open = expanded === entry.id;

        return (
          <Card key={entry.id} withBorder radius="md" padding="sm">
            <Stack gap="xs">
              <Group justify="space-between" align="center" wrap="nowrap" gap="xs">
                <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                  <LevelBadge entry={entry} />
                  <Text size="xs" c="dimmed" ff="monospace" style={{ minWidth: 0 }}>
                    {formatDateTime(entry.occurred_at)}
                  </Text>
                </Group>
                {hasDetails(entry) && (
                  <ExpandToggle open={open} onToggle={() => toggle(entry.id)} />
                )}
              </Group>

              <Component entry={entry} />

              <Text size="sm" className="break-anywhere">
                {entry.message}
              </Text>

              <Collapse expanded={open}>
                <Box pt={4}>
                  <EntryDetails entry={entry} />
                </Box>
              </Collapse>
            </Stack>
          </Card>
        );
      })}
    </Stack>
  );
}

function LevelBadge({ entry }: { entry: IndexerLogEntry }) {
  const { t } = useTranslation();

  return (
    <Badge color={INDEXER_LOG_LEVEL_COLOR[entry.level]} variant="light" size="sm">
      {t(`indexers.logs.levels.${entry.level}`)}
    </Badge>
  );
}

function Component({ entry }: { entry: IndexerLogEntry }) {
  const { t } = useTranslation();

  return (
    <Text size="sm" c={entry.component ? undefined : 'dimmed'} className="break-anywhere">
      {entry.component ?? t('indexers.logs.noComponent')}
    </Text>
  );
}

function ExpandToggle({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  const { t } = useTranslation();

  return (
    <ActionIcon
      variant="subtle"
      color="gray"
      aria-expanded={open}
      aria-label={t('indexers.logs.toggleDetails')}
      onClick={(event) => {
        event.stopPropagation();
        onToggle();
      }}
    >
      {open ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
    </ActionIcon>
  );
}

function EntryDetails({ entry }: { entry: IndexerLogEntry }) {
  const { t } = useTranslation();

  return (
    <Stack gap={6}>
      <Group gap="md" wrap="wrap">
        {entry.method && (
          <Text size="xs" c="dimmed">
            {t('indexers.logs.method')}: {entry.method}
          </Text>
        )}
        {entry.exception_type && (
          <Text size="xs" c="dimmed" className="break-anywhere">
            {entry.exception_type}
          </Text>
        )}
      </Group>
      {entry.exception && (
        <Code block className="break-anywhere">
          {entry.exception}
        </Code>
      )}
    </Stack>
  );
}
