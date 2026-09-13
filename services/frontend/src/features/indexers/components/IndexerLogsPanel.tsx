import { Select } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { IndexerLogsTable } from '@/features/indexers/components/IndexerLogsTable';
import { PagedSection } from '@/features/indexers/components/PagedSection';
import { INDEXER_LOG_LEVELS, isIndexerLogLevel } from '@/features/indexers/events';
import { HISTORY_PAGE_SIZE, useIndexerLogs } from '@/features/indexers/queries';
import type { IndexerLogLevel } from '@/types';

const ALL = 'all';

/** Prowlarr's own log, the view its UI calls System → Events. */
export function IndexerLogsPanel({ active }: { active: boolean }) {
  const { t } = useTranslation();
  const [minLevel, setMinLevel] = useState<IndexerLogLevel | undefined>(undefined);
  const [page, setPage] = useState(1);

  const logs = useIndexerLogs({ page, minLevel }, active);

  const entries = logs.data?.logs ?? [];
  const total = logs.data?.total ?? 0;

  const changeLevel = (value: string | null) => {
    setMinLevel(isIndexerLogLevel(value) ? value : undefined);
    // A page number from the previous filter rarely exists in the new result.
    setPage(1);
  };

  return (
    <PagedSection
      i18nBase="indexers.logs"
      loading={logs.isLoading}
      fetching={logs.isFetching}
      error={logs.error}
      onRetry={() => void logs.refetch()}
      isEmpty={entries.length === 0}
      isFiltered={minLevel !== undefined}
      page={page}
      lastPage={Math.max(1, Math.ceil(total / HISTORY_PAGE_SIZE))}
      total={total}
      onPageChange={setPage}
      filters={
        <Select
          label={t('indexers.logs.filterLevel')}
          value={minLevel ?? ALL}
          onChange={changeLevel}
          allowDeselect={false}
          w={{ base: '100%', sm: 220 }}
          data={[
            { value: ALL, label: t('indexers.logs.allLevels') },
            ...INDEXER_LOG_LEVELS.map((level) => ({
              value: level,
              label: t(`indexers.logs.levels.${level}`),
            })),
          ]}
        />
      }
    >
      <IndexerLogsTable entries={entries} />
    </PagedSection>
  );
}
