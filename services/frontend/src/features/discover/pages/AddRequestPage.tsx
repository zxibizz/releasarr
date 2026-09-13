import {
  Alert,
  Badge,
  Button,
  Group,
  Paper,
  SimpleGrid,
  Skeleton,
  Stack,
  Tabs,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { AddRequestModal } from '@/features/discover/components/AddRequestModal';
import { MediaSearchResultCard } from '@/features/discover/components/MediaSearchResultCard';
import { useMediaSearch } from '@/features/discover/queries';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { MediaSearchResult } from '@/types';
import { getErrorMessage } from '@/utils/errors';

type ResultTab = MediaSearchResult['type'];

const RESULT_TABS: readonly ResultTab[] = ['movie', 'series'];

const TAB_LABELS: Record<ResultTab, string> = {
  movie: 'discover.tabs.movies',
  series: 'discover.tabs.shows',
};

function ResultsSkeleton() {
  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
      {Array.from({ length: 4 }).map((_, index) => (
        <Paper key={index} withBorder radius="lg" p="lg">
          <Stack gap="sm">
            <Skeleton height={20} width="60%" />
            <Skeleton height={12} />
            <Skeleton height={12} width="80%" />
            <Skeleton height={28} width={120} radius="xl" />
          </Stack>
        </Paper>
      ))}
    </SimpleGrid>
  );
}

export function AddRequestPage() {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  const [term, setTerm] = useState('');
  // Kept apart from the field so every keystroke does not hit TVDB, Sonarr and
  // the request table; the query only moves on submit.
  const [submitted, setSubmitted] = useState('');
  const [picked, setPicked] = useState<MediaSearchResult | null>(null);
  // Null until the reader picks a tab, which leaves every fresh search free to
  // open whichever tab its best hit landed in.
  const [chosenTab, setChosenTab] = useState<ResultTab | null>(null);

  const search = useMediaSearch(submitted);
  const results = search.data?.results ?? [];

  const grouped: Record<ResultTab, MediaSearchResult[]> = {
    movie: results.filter((result) => result.type === 'movie'),
    series: results.filter((result) => result.type === 'series'),
  };

  /*
   * The search covers both kinds at once and comes back as one list already
   * ranked across the two providers, so whichever kind took the top spot is the
   * kind the term was most likely about. Opening that tab saves the reader from
   * finding an empty-handed Movies tab when they searched for a series.
   */
  const activeTab =
    chosenTab && grouped[chosenTab].length > 0 ? chosenTab : (results[0]?.type ?? 'series');

  return (
    <Stack gap={isMobile ? 'md' : 'xl'}>
      <Stack gap={4}>
        <Title order={1}>{t('discover.title')}</Title>
        {!isMobile && <Text c="dimmed">{t('discover.subtitle')}</Text>}
      </Stack>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          setSubmitted(term.trim());
          setChosenTab(null);
        }}
      >
        <Group gap="sm" wrap="nowrap" align="flex-end">
          <TextInput
            type="search"
            enterKeyHint="search"
            style={{ flex: 1, minWidth: 0 }}
            value={term}
            onChange={(event) => setTerm(event.currentTarget.value)}
            placeholder={t('discover.searchPlaceholder')}
            aria-label={t('discover.searchPlaceholder')}
          />
          <Button type="submit" loading={search.isFetching} disabled={!term.trim()}>
            {t('discover.actions.search')}
          </Button>
        </Group>
      </form>

      {search.isError && (
        <Alert color="red" radius="lg" title={t('discover.error.title')}>
          <Stack align="flex-start" gap="sm">
            <Text>{getErrorMessage(search.error, t('discover.error.description'))}</Text>
            <Button variant="light" size="xs" onClick={() => void search.refetch()}>
              {t('common.tryAgain')}
            </Button>
          </Stack>
        </Alert>
      )}

      {search.isLoading && <ResultsSkeleton />}

      {!search.isLoading && !search.isError && results.length > 0 && (
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <Title order={3}>{t('discover.results.heading')}</Title>
            <Text c="dimmed" size="sm">
              {t('discover.results.count', { count: results.length })}
            </Text>
          </Group>
          <Tabs
            value={activeTab}
            onChange={(value) => setChosenTab(value === 'movie' ? 'movie' : 'series')}
            // An inactive tab renders nothing rather than hiding a second grid
            // of cards, each of which loads a poster.
            keepMounted={false}
          >
            <Tabs.List mb="lg">
              {RESULT_TABS.map((tab) => (
                <Tabs.Tab
                  key={tab}
                  value={tab}
                  disabled={grouped[tab].length === 0}
                  rightSection={
                    <Badge size="sm" variant="light" circle>
                      {grouped[tab].length}
                    </Badge>
                  }
                >
                  {t(TAB_LABELS[tab])}
                </Tabs.Tab>
              ))}
            </Tabs.List>

            {RESULT_TABS.map((tab) => (
              <Tabs.Panel key={tab} value={tab}>
                <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
                  {grouped[tab].map((result) => (
                    <MediaSearchResultCard
                      key={`${result.type}-${result.provider_id}`}
                      result={result}
                      onPick={setPicked}
                    />
                  ))}
                </SimpleGrid>
              </Tabs.Panel>
            ))}
          </Tabs>
        </Stack>
      )}

      {submitted && !search.isLoading && !search.isError && results.length === 0 && (
        <EmptyState
          icon="🔍"
          title={t('discover.empty.title')}
          description={t('discover.empty.description')}
        />
      )}

      {!submitted && (
        <EmptyState
          icon="🧭"
          title={t('discover.start.title')}
          description={t('discover.start.description')}
        />
      )}

      <AddRequestModal media={picked} onClose={() => setPicked(null)} />
    </Stack>
  );
}
