import { Select } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { IndexerHistoryTable } from '@/features/indexers/components/IndexerHistoryTable';
import { PagedSection } from '@/features/indexers/components/PagedSection';
import { INDEXER_EVENT_TYPES, isIndexerEventType } from '@/features/indexers/events';
import { HISTORY_PAGE_SIZE, useIndexerHistory } from '@/features/indexers/queries';
import type { Indexer, IndexerEventType } from '@/types';

const ALL = 'all';

interface IndexerHistoryPanelProps {
  /** Populates the indexer filter; the history itself names its own indexers. */
  indexers: Indexer[];
  active: boolean;
}

/** Prowlarr's per-indexer record of searches, feed refreshes and grabs. */
export function IndexerHistoryPanel({ indexers, active }: IndexerHistoryPanelProps) {
  const { t } = useTranslation();
  const [indexerId, setIndexerId] = useState<number | undefined>(undefined);
  const [eventType, setEventType] = useState<IndexerEventType | undefined>(undefined);
  const [page, setPage] = useState(1);

  const history = useIndexerHistory({ page, indexerId, eventType }, active);

  const entries = history.data?.history ?? [];
  const total = history.data?.total ?? 0;

  // A page number from the previous filter rarely exists in the new result.
  const changeIndexer = (value: string | null) => {
    setIndexerId(value === null || value === ALL ? undefined : Number(value));
    setPage(1);
  };

  const changeEventType = (value: string | null) => {
    setEventType(isIndexerEventType(value) ? value : undefined);
    setPage(1);
  };

  return (
    <PagedSection
      i18nBase="indexers.history"
      loading={history.isLoading}
      fetching={history.isFetching}
      error={history.error}
      onRetry={() => void history.refetch()}
      isEmpty={entries.length === 0}
      isFiltered={indexerId !== undefined || eventType !== undefined}
      page={page}
      lastPage={Math.max(1, Math.ceil(total / HISTORY_PAGE_SIZE))}
      total={total}
      onPageChange={setPage}
      filters={
        <>
          <Select
            label={t('indexers.history.filterIndexer')}
            value={indexerId === undefined ? ALL : String(indexerId)}
            onChange={changeIndexer}
            allowDeselect={false}
            w={{ base: '100%', sm: 220 }}
            data={[
              { value: ALL, label: t('indexers.history.allIndexers') },
              ...indexers.map((indexer) => ({ value: String(indexer.id), label: indexer.name })),
            ]}
          />
          <Select
            label={t('indexers.history.filterEvent')}
            value={eventType ?? ALL}
            onChange={changeEventType}
            allowDeselect={false}
            w={{ base: '100%', sm: 220 }}
            data={[
              { value: ALL, label: t('indexers.history.allEvents') },
              ...INDEXER_EVENT_TYPES.map((kind) => ({
                value: kind,
                label: t(`indexers.history.events.${kind}`),
              })),
            ]}
          />
        </>
      }
    >
      <IndexerHistoryTable entries={entries} />
    </PagedSection>
  );
}
