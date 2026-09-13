import { ActionIcon, Badge, Box, Card, Collapse, Group, Stack, Table, Text } from '@mantine/core';
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { formatElapsed } from '@/features/indexers/events';
import { formatLogContext } from '@/features/logs/context';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { IndexerHistoryEntry } from '@/types';
import { formatDateTime } from '@/utils/formatters';
import { getIndexerEventColor } from '@/utils/status';

const COLUMN_COUNT = 5;

interface EntryView {
  /** The one line worth a column of its own: what was searched, or what was grabbed. */
  subject: string | null;
  context: string | null;
  elapsed: string | null;
  hasDetails: boolean;
}

const describe = (entry: IndexerHistoryEntry): EntryView => {
  const subject = entry.query ?? entry.title ?? null;
  const context = formatLogContext(entry.data);
  const elapsed = formatElapsed(entry.elapsed_ms);

  return {
    subject,
    context,
    elapsed,
    hasDetails: Boolean(context || elapsed || entry.source),
  };
};

export function IndexerHistoryTable({ entries }: { entries: IndexerHistoryEntry[] }) {
  const isMobile = useIsMobile();

  return isMobile ? <HistoryCards entries={entries} /> : <HistoryGrid entries={entries} />;
}

function HistoryGrid({ entries }: { entries: IndexerHistoryEntry[] }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<number | null>(null);

  const toggle = (id: number) => setExpanded((current) => (current === id ? null : id));

  return (
    <Table.ScrollContainer minWidth={720}>
      <Table verticalSpacing="xs" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={44} />
            <Table.Th w={150}>{t('indexers.history.columns.time')}</Table.Th>
            <Table.Th w={150}>{t('indexers.history.columns.event')}</Table.Th>
            <Table.Th w={170}>{t('indexers.history.columns.indexer')}</Table.Th>
            <Table.Th>{t('indexers.history.columns.detail')}</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {entries.map((entry) => {
            const open = expanded === entry.id;
            const view = describe(entry);

            return [
              <Table.Tr
                key={entry.id}
                onClick={() => view.hasDetails && toggle(entry.id)}
                style={{ cursor: view.hasDetails ? 'pointer' : 'default' }}
              >
                <Table.Td>
                  {view.hasDetails && <ExpandToggle open={open} onToggle={() => toggle(entry.id)} />}
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed" ff="monospace">
                    {formatDateTime(entry.occurred_at)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <EventBadge entry={entry} />
                </Table.Td>
                <Table.Td>
                  <IndexerName entry={entry} />
                </Table.Td>
                <Table.Td>
                  <Subject subject={view.subject} />
                </Table.Td>
              </Table.Tr>,

              <Table.Tr key={`${entry.id}-details`}>
                <Table.Td colSpan={COLUMN_COUNT} p={0} style={{ borderBottom: 'none' }}>
                  <Collapse expanded={open}>
                    <Box px="md" py="sm">
                      <EntryDetails entry={entry} view={view} />
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

function HistoryCards({ entries }: { entries: IndexerHistoryEntry[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  const toggle = (id: number) => setExpanded((current) => (current === id ? null : id));

  return (
    <Stack gap="xs">
      {entries.map((entry) => {
        const open = expanded === entry.id;
        const view = describe(entry);

        return (
          <Card key={entry.id} withBorder radius="md" padding="sm">
            <Stack gap="xs">
              <Group justify="space-between" align="center" wrap="nowrap" gap="xs">
                <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                  <EventBadge entry={entry} />
                  <Text size="xs" c="dimmed" ff="monospace" style={{ minWidth: 0 }}>
                    {formatDateTime(entry.occurred_at)}
                  </Text>
                </Group>
                {view.hasDetails && <ExpandToggle open={open} onToggle={() => toggle(entry.id)} />}
              </Group>

              <IndexerName entry={entry} />
              <Subject subject={view.subject} />

              <Collapse expanded={open}>
                <Box pt={4}>
                  <EntryDetails entry={entry} view={view} />
                </Box>
              </Collapse>
            </Stack>
          </Card>
        );
      })}
    </Stack>
  );
}

function EventBadge({ entry }: { entry: IndexerHistoryEntry }) {
  const { t } = useTranslation();

  return (
    <Badge
      color={getIndexerEventColor(entry.event_type, entry.successful)}
      variant="light"
      size="sm"
    >
      {t(`indexers.history.events.${entry.event_type}`)}
    </Badge>
  );
}

function IndexerName({ entry }: { entry: IndexerHistoryEntry }) {
  return (
    <Text size="sm" c={entry.indexer_name ? undefined : 'dimmed'}>
      {entry.indexer_name ?? `#${entry.indexer_id}`}
    </Text>
  );
}

function Subject({ subject }: { subject: string | null }) {
  const { t } = useTranslation();

  if (!subject) {
    return (
      <Text size="sm" c="dimmed">
        {t('indexers.history.noDetail')}
      </Text>
    );
  }

  return (
    <Text size="sm" className="break-anywhere">
      {subject}
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
      aria-label={t('indexers.history.toggleDetails')}
      onClick={(event) => {
        event.stopPropagation();
        onToggle();
      }}
    >
      {open ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
    </ActionIcon>
  );
}

function EntryDetails({ entry, view }: { entry: IndexerHistoryEntry; view: EntryView }) {
  const { t } = useTranslation();

  return (
    <Stack gap={6}>
      <Group gap="md" wrap="wrap">
        {entry.source && (
          <Text size="xs" c="dimmed">
            {t('indexers.history.source')}: {entry.source}
          </Text>
        )}
        {view.elapsed && (
          <Text size="xs" c="dimmed">
            {t('indexers.history.elapsed')}: {view.elapsed}
          </Text>
        )}
      </Group>
      {view.context && (
        <Text size="xs" c="dimmed" ff="monospace" className="break-anywhere">
          {view.context}
        </Text>
      )}
    </Stack>
  );
}
