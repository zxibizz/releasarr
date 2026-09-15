import {
  Alert,
  Button,
  Card,
  Group,
  Paper,
  Skeleton,
  Stack,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { ManualReleaseForm } from '@/features/releases/components/ManualReleaseForm';
import {
  ReleaseFilters,
  ReleaseFiltersToggle,
} from '@/features/releases/components/ReleaseFilters';
import { ReleaseResults } from '@/features/releases/components/ReleaseResults';
import {
  DEFAULT_SOURCE_FILTER,
  DEFAULT_SORT_FIELD,
  MANUAL_TAB,
  NATURAL_SORT_ORDER,
  SEARCH_TAB,
  useReleaseSearch,
} from '@/features/releases/useReleaseSearch';
import type { RequestTitle } from '@/features/requests/localization';
import { useIsMobile } from '@/hooks/useIsMobile';
import { getErrorMessage } from '@/utils/errors';

/*
 * A step below Mantine's smallest preset, for the row of query hints under the
 * field. They are shortcuts for filling it in, not actions in their own right,
 * and at `compact-xs` they read as loud as the Search button beside them.
 */
const HINT_SIZE = { h: 20, px: 7, fz: 11 } as const;

interface ReleaseSearchProps {
  requestId: string;
  requestTitle: string;
  prefillQuery?: string;
  /** The titles the query can be refilled from, once it has been edited away. */
  titleOptions?: RequestTitle[];
  /** The season a series request covers, which the query can be narrowed to. */
  seasonNumber?: number;
  focusToken?: number;
  onDownloadQueued: () => void;
}

export function ReleaseSearch({
  requestId,
  requestTitle,
  prefillQuery,
  titleOptions = [],
  seasonNumber,
  focusToken = 0,
  onDownloadQueued,
}: ReleaseSearchProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const {
    activeTab,
    setActiveTab,
    query,
    setQuery,
    results,
    failedIndexers,
    dismissFailedIndexers,
    searchedQuery,
    sortField,
    setSortField,
    sortOrder,
    setSortOrder,
    sourceFilter,
    setSourceFilter,
    downloadingId,
    setDownloadingId,
    filtersExpanded,
    setFiltersExpanded,
    normalizedQuery,
    seasonToken,
    seasonInQuery,
    search,
    download,
    inputRef,
    sources,
    visibleResults,
    handleSubmit,
    handleClear,
  } = useReleaseSearch({
    requestId,
    prefillQuery,
    seasonNumber,
    focusToken,
    onDownloadQueued,
  });

  // The phone renders a textarea and the desktop an input, so the ref is
  // assigned by hand rather than typed to one element.
  const assignInputRef = (node: HTMLInputElement | HTMLTextAreaElement | null) => {
    inputRef.current = node;
  };

  // Only stretch the actions on a phone; growing them on desktop shrinks the
  // labels below their content width and clips them.
  const actionFlex = isMobile ? 1 : undefined;

  // Anything a collapsed panel is hiding shows as a dot on the toggle, so a
  // narrowed or reordered result list is never unexplained.
  const filtersAdjusted =
    sortField !== DEFAULT_SORT_FIELD ||
    sortOrder !== NATURAL_SORT_ORDER[DEFAULT_SORT_FIELD] ||
    sourceFilter !== DEFAULT_SOURCE_FILTER;

  return (
    <Card withBorder radius="lg" padding={isMobile ? 'sm' : 'lg'}>
      <Tabs value={activeTab} onChange={(value) => setActiveTab(value ?? SEARCH_TAB)}>
        {/* Long labels wrapped the list into two stacked rows on a phone,
            which read as two links rather than one tab bar. */}
        <Tabs.List grow mb="lg">
          <Tabs.Tab value={SEARCH_TAB}>{t('releaseSearch.tabs.search')}</Tabs.Tab>
          <Tabs.Tab value={MANUAL_TAB}>{t('releaseSearch.tabs.manual')}</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value={SEARCH_TAB}>
          <Stack gap="lg">
            <form onSubmit={handleSubmit}>
              <Stack gap="xs">
                <Group align="flex-end" gap="sm" wrap="wrap">
                  {isMobile ? (
                    /*
                      Queries here are whole release titles — the prefilled
                      request title alone outruns a phone-width field, and a
                      single line hid everything but its first few words behind
                      a horizontal scroll. The field grows to show the query
                      instead, up to four lines.
                    */
                    <Textarea
                      ref={assignInputRef}
                      autosize
                      minRows={1}
                      maxRows={4}
                      w="100%"
                      value={query}
                      onChange={(event) => setQuery(event.currentTarget.value)}
                      placeholder={t('releaseSearch.placeholder', { title: requestTitle })}
                      aria-label={t('releaseSearch.ariaLabel', { title: requestTitle })}
                    />
                  ) : (
                    <TextInput
                      ref={assignInputRef}
                      type="search"
                      enterKeyHint="search"
                      style={{ flex: '1 1 220px', minWidth: 0 }}
                      value={query}
                      onChange={(event) => setQuery(event.currentTarget.value)}
                      placeholder={t('releaseSearch.placeholder', { title: requestTitle })}
                      aria-label={t('releaseSearch.ariaLabel', { title: requestTitle })}
                    />
                  )}
                  <Group gap="sm" wrap="nowrap" w={{ base: '100%', sm: 'auto' }}>
                    <Button
                      type="submit"
                      loading={search.isPending}
                      disabled={!normalizedQuery}
                      style={{ flex: actionFlex }}
                    >
                      {t('releaseSearch.actions.search')}
                    </Button>
                    {(query || results.length > 0) && (
                      <Button
                        type="button"
                        variant="default"
                        onClick={handleClear}
                        style={{ flex: actionFlex }}
                      >
                        {t('releaseSearch.actions.clear')}
                      </Button>
                    )}
                  </Group>
                </Group>

                {/*
                  A release is indexed under whichever title its group used, so
                  a search that finds nothing under the translated name often
                  finds plenty under the original. These put either back in the
                  field after it has been cleared or typed over; the one already
                  in the field is the one that cannot be filled again.
                */}
                {(titleOptions.length > 0 || seasonToken) && (
                  <Group gap={6} wrap="wrap" align="center">
                    {titleOptions.length > 0 && (
                      <>
                        <Text {...HINT_SIZE} c="dimmed">
                          {t('releaseSearch.fill.label')}
                        </Text>
                        {titleOptions.map((option) => (
                          <Button
                            key={option.language}
                            type="button"
                            size="compact-xs"
                            variant="default"
                            {...HINT_SIZE}
                            disabled={normalizedQuery === option.title}
                            onClick={() => setQuery(option.title)}
                          >
                            {option.label}
                          </Button>
                        ))}
                      </>
                    )}
                    {seasonToken && (
                      <Button
                        type="button"
                        size="compact-xs"
                        variant="default"
                        {...HINT_SIZE}
                        leftSection={<IconPlus size={10} />}
                        // The plus sign is the only mark of it adding to the
                        // query rather than replacing it, and that is not a
                        // thing an icon can say on its own.
                        aria-label={t('releaseSearch.fill.appendSeason', { season: seasonToken })}
                        disabled={!normalizedQuery || seasonInQuery}
                        onClick={() => setQuery(`${normalizedQuery} ${seasonToken}`)}
                      >
                        {seasonToken}
                      </Button>
                    )}
                  </Group>
                )}
              </Stack>
            </form>

            {search.isPending && (
              <Stack gap="sm">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Paper key={index} withBorder radius="md" p="md">
                    <Skeleton height={14} width="70%" mb="xs" />
                    <Skeleton height={10} width="40%" />
                  </Paper>
                ))}
              </Stack>
            )}

            {search.isError && (
              <Alert color="red" radius="md">
                {getErrorMessage(search.error, t('releaseSearch.toasts.searchFailedFallback'))}
              </Alert>
            )}

            {failedIndexers.length > 0 && (
              <Alert
                color="yellow"
                radius="md"
                title={t('releaseSearch.indexerFailures.title')}
                withCloseButton
                onClose={dismissFailedIndexers}
              >
                {t('releaseSearch.indexerFailures.description', {
                  count: failedIndexers.length,
                  names: failedIndexers.map((indexer) => indexer.name).join(', '),
                })}
              </Alert>
            )}

            {visibleResults.length > 0 && (
              <Stack gap="md">
                <Group justify="space-between" wrap="wrap" gap="xs">
                  <Title order={5}>{t('releaseSearch.results.heading')}</Title>
                  <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                    <Text size="sm" c="dimmed">
                      {t(
                        visibleResults.length === results.length
                          ? 'releaseSearch.results.summary'
                          : 'releaseSearch.results.summaryWithTotal',
                        {
                          count: visibleResults.length,
                          total: results.length,
                          query: searchedQuery,
                        },
                      )}
                    </Text>
                    {isMobile && (
                      <ReleaseFiltersToggle
                        adjusted={filtersAdjusted}
                        expanded={filtersExpanded}
                        setExpanded={setFiltersExpanded}
                      />
                    )}
                  </Group>
                </Group>

                {/*
                  Two rows of sort and source controls on a phone pushed the
                  candidates themselves below the fold, and the default order —
                  freshest first, every source — is the one wanted almost every
                  time. Unmounted while closed so the hidden controls stay out
                  of the tab order.
                */}
                <ReleaseFilters
                  isMobile={isMobile}
                  sources={sources}
                  sortField={sortField}
                  setSortField={setSortField}
                  sortOrder={sortOrder}
                  setSortOrder={setSortOrder}
                  sourceFilter={sourceFilter}
                  setSourceFilter={setSourceFilter}
                  expanded={filtersExpanded}
                />

                <ReleaseResults
                  results={visibleResults}
                  downloadingId={downloadingId}
                  setDownloadingId={setDownloadingId}
                  download={download}
                />
              </Stack>
            )}

            {searchedQuery && !search.isPending && visibleResults.length === 0 && (
              <Paper withBorder radius="lg" p={{ base: 'md', sm: 'xl' }}>
                <Stack align="center" gap="xs">
                  <Text fz={32}>🔍</Text>
                  <Title order={5}>{t('releaseSearch.empty.title')}</Title>
                  <Text size="sm" c="dimmed" ta="center">
                    {t('releaseSearch.empty.description')}
                  </Text>
                </Stack>
              </Paper>
            )}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value={MANUAL_TAB}>
          <ManualReleaseForm requestId={requestId} onDownloadQueued={onDownloadQueued} />
        </Tabs.Panel>
      </Tabs>
    </Card>
  );
}
