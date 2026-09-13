import { Stack, Tabs, Text } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ResponsiveModal } from '@/components/ResponsiveModal';
import { IndexerHistoryPanel } from '@/features/indexers/components/IndexerHistoryPanel';
import { IndexerLogsPanel } from '@/features/indexers/components/IndexerLogsPanel';
import type { Indexer } from '@/types';

interface IndexerLogsModalProps {
  indexers: Indexer[];
  opened: boolean;
  onClose: () => void;
}

type Tab = 'events' | 'history';

/**
 * Everything Prowlarr will tell us about what its indexers have been doing.
 *
 * The two tabs are separate Prowlarr endpoints rather than two views of one
 * list: Events is its application log, where a broken indexer explains itself,
 * and History is its per-indexer record of searches and grabs. Both stay mounted
 * so switching tabs keeps each one's filters, and each only queries while
 * showing, since every call reaches Prowlarr.
 */
export function IndexerLogsModal({ indexers, opened, onClose }: IndexerLogsModalProps) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>('events');

  return (
    <ResponsiveModal opened={opened} onClose={onClose} title={t('indexers.logsModal.title')}>
      <Stack gap="sm">
        <Text size="sm" c="dimmed">
          {t('indexers.logsModal.description')}
        </Text>

        <Tabs value={tab} onChange={(value) => setTab(value === 'history' ? 'history' : 'events')}>
          <Tabs.List mb="md">
            <Tabs.Tab value="events">{t('indexers.logsModal.tabs.events')}</Tabs.Tab>
            <Tabs.Tab value="history">{t('indexers.logsModal.tabs.history')}</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="events">
            <IndexerLogsPanel active={opened && tab === 'events'} />
          </Tabs.Panel>
          <Tabs.Panel value="history">
            <IndexerHistoryPanel indexers={indexers} active={opened && tab === 'history'} />
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </ResponsiveModal>
  );
}
