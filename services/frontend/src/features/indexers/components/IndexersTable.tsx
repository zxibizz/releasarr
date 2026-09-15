import { ActionIcon, Card, Group, Stack, Table, Text, Tooltip } from '@mantine/core';
import { IconPlugConnected } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { DataField } from '@/components/DataField';
import { StatusBadge } from '@/components/StatusBadge';
import { useTestIndexer } from '@/features/indexers/queries';
import { formatRelativeTime } from '@/features/tasks/formatting';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { Indexer } from '@/types';
import { formatDateTime } from '@/utils/formatters';

interface IndexersTableProps {
  indexers: Indexer[];
}

export function IndexersTable({ indexers }: IndexersTableProps) {
  const isMobile = useIsMobile();

  return isMobile ? <IndexersCards indexers={indexers} /> : <IndexersGrid indexers={indexers} />;
}

function IndexersGrid({ indexers }: IndexersTableProps) {
  const { t, i18n } = useTranslation();

  return (
    <Table.ScrollContainer minWidth={720}>
      <Table highlightOnHover verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>{t('indexers.columns.name')}</Table.Th>
            <Table.Th>{t('indexers.columns.health')}</Table.Th>
            <Table.Th>{t('indexers.columns.protocol')}</Table.Th>
            <Table.Th>{t('indexers.columns.priority')}</Table.Th>
            <Table.Th>{t('indexers.columns.lastFailure')}</Table.Th>
            <Table.Th w={60} />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {indexers.map((indexer) => (
            <Table.Tr key={indexer.id}>
              <Table.Td>
                <Text fw={600} size="sm">
                  {indexer.name}
                </Text>
                <Capabilities indexer={indexer} />
              </Table.Td>
              <Table.Td>
                <HealthBadge indexer={indexer} locale={i18n.language} />
              </Table.Td>
              <Table.Td>
                <Text size="sm" c={indexer.protocol ? undefined : 'dimmed'}>
                  {indexer.protocol ?? '—'}
                </Text>
                <Text size="xs" c="dimmed">
                  {indexer.privacy ?? ''}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm" c={indexer.priority == null ? 'dimmed' : undefined}>
                  {indexer.priority ?? '—'}
                </Text>
              </Table.Td>
              <Table.Td>
                <Timestamp value={indexer.most_recent_failure} locale={i18n.language} />
              </Table.Td>
              <Table.Td>
                <TestButton indexer={indexer} />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

function IndexersCards({ indexers }: IndexersTableProps) {
  const { t, i18n } = useTranslation();

  return (
    <Stack gap="xs" p="xs">
      {indexers.map((indexer) => (
        <Card key={indexer.id} withBorder radius="md" padding="sm">
          <Stack gap="xs">
            <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
              <Stack gap={2} style={{ minWidth: 0 }}>
                <Group gap="xs" wrap="nowrap">
                  <Text fw={600} size="sm">
                    {indexer.name}
                  </Text>
                  <HealthBadge indexer={indexer} locale={i18n.language} />
                </Group>
                <Capabilities indexer={indexer} />
              </Stack>
              <TestButton indexer={indexer} />
            </Group>

            <Stack gap={4}>
              <DataField label={t('indexers.columns.protocol')}>
                <Text size="sm" c={indexer.protocol ? undefined : 'dimmed'}>
                  {[indexer.protocol, indexer.privacy].filter(Boolean).join(' · ') || '—'}
                </Text>
              </DataField>
              <DataField label={t('indexers.columns.priority')}>
                <Text size="sm" c={indexer.priority == null ? 'dimmed' : undefined}>
                  {indexer.priority ?? '—'}
                </Text>
              </DataField>
              <DataField label={t('indexers.columns.lastFailure')}>
                <Timestamp value={indexer.most_recent_failure} locale={i18n.language} />
              </DataField>
            </Stack>
          </Stack>
        </Card>
      ))}
    </Stack>
  );
}

/**
 * The health badge, with the reason behind it on hover.
 *
 * "Blocked" is the state a reader most needs explained: the badge says an
 * indexer is unusable, and only the retry time says for how long.
 */
function HealthBadge({ indexer, locale }: { indexer: Indexer; locale: string }) {
  const { t } = useTranslation();
  const badge = <StatusBadge status={indexer.health} size="sm" />;

  if (indexer.health === 'blocked' && indexer.disabled_till) {
    return (
      <Tooltip
        label={t('indexers.blockedUntil', {
          when: formatRelativeTime(indexer.disabled_till, locale),
        })}
        multiline
        maw={320}
      >
        {badge}
      </Tooltip>
    );
  }

  if (indexer.health === 'degraded') {
    return (
      <Tooltip label={t('indexers.degradedHint')} multiline maw={320}>
        {badge}
      </Tooltip>
    );
  }

  return badge;
}

function Capabilities({ indexer }: { indexer: Indexer }) {
  const { t } = useTranslation();

  const capabilities = [
    indexer.supports_search ? t('indexers.capabilities.search') : null,
    indexer.supports_rss ? t('indexers.capabilities.rss') : null,
  ].filter(Boolean);

  return (
    <Text size="xs" c="dimmed">
      {capabilities.length > 0 ? capabilities.join(' · ') : t('indexers.capabilities.none')}
    </Text>
  );
}

function TestButton({ indexer }: { indexer: Indexer }) {
  const { t } = useTranslation();
  const testIndexer = useTestIndexer();

  return (
    <Tooltip label={t('indexers.testNow')}>
      <ActionIcon
        variant="subtle"
        color="blue"
        aria-label={t('indexers.testIndexer', { name: indexer.name })}
        loading={testIndexer.isPending}
        onClick={() => testIndexer.mutate(indexer.id)}
      >
        <IconPlugConnected size={16} />
      </ActionIcon>
    </Tooltip>
  );
}

function Timestamp({ value, locale }: { value: string | null | undefined; locale: string }) {
  const { t } = useTranslation();

  if (!value) {
    return (
      <Text size="sm" c="dimmed">
        {t('indexers.never')}
      </Text>
    );
  }

  return (
    <Tooltip label={formatDateTime(value)}>
      <Text size="sm">{formatRelativeTime(value, locale)}</Text>
    </Tooltip>
  );
}
