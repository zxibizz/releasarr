import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  Card,
  Flex,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Input,
  Select,
  Skeleton,
  SkeletonText,
  Spinner,
  Stack,
  Tag,
  Text,
  VisuallyHidden,
  useToast,
} from '@chakra-ui/react';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useReleaseSearch } from '@/hooks/useReleaseSearch';
import type { ReleaseSearchResult } from '@/types';

interface ReleaseSearchProps {
  requestId: string;
  requestTitle: string;
  onDownloadQueued?: () => void;
  prefillQuery?: string | null;
  focusTrigger?: number;
}

const qualityColorScheme: Record<string, string> = {
  '2160p': 'purple',
  '1080p': 'blue',
  '720p': 'green',
};

export const ReleaseSearch: React.FC<ReleaseSearchProps> = ({
  requestId,
  requestTitle,
  onDownloadQueued,
  prefillQuery,
  focusTrigger,
}) => {
  const { searchState, search, clearSearch, selectReleaseCandidate } = useReleaseSearch();
  const [query, setQuery] = useState(prefillQuery ?? '');
  const [downloadingCandidateId, setDownloadingCandidateId] = useState<string | null>(null);
  const [sortField, setSortField] = useState<'seeders' | 'leechers' | 'size'>('seeders');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const inputRef = useRef<HTMLInputElement | null>(null);
  const toast = useToast();
  const { t } = useTranslation();

  const parseSizeToBytes = useCallback((size: string | null | undefined): number | null => {
    if (!size) {
      return null;
    }
    const match = size.trim().match(/^([\d.]+)\s*([KMGTPE]?B)$/i);
    if (!match) {
      return null;
    }
    const value = Number.parseFloat(match[1]);
    if (Number.isNaN(value)) {
      return null;
    }
    const unit = match[2].toUpperCase();
    const multipliers: Record<string, number> = {
      B: 1,
      KB: 1024,
      MB: 1024 ** 2,
      GB: 1024 ** 3,
      TB: 1024 ** 4,
      PB: 1024 ** 5,
    };
    const multiplier = multipliers[unit];
    if (!multiplier) {
      return null;
    }
    return value * multiplier;
  }, []);

  const uniqueSources = useMemo(() => {
    const sources = new Set<string>();
    searchState.results.forEach((result) => {
      if (result.source) {
        sources.add(result.source);
      }
    });
    return Array.from(sources).sort((a, b) => a.localeCompare(b));
  }, [searchState.results]);

  useEffect(() => {
    if (sourceFilter !== 'all' && !uniqueSources.includes(sourceFilter)) {
      setSourceFilter('all');
    }
  }, [sourceFilter, uniqueSources]);

  const displayedResults = useMemo(() => {
    const working = [...searchState.results];

    const filtered = sourceFilter === 'all'
      ? working
      : working.filter((result) => result.source === sourceFilter);

    const getSortValue = (candidate: ReleaseSearchResult): number | null => {
      switch (sortField) {
        case 'seeders':
          return candidate.seeders ?? null;
        case 'leechers':
          return candidate.leechers ?? null;
        case 'size':
          return parseSizeToBytes(candidate.size);
        default:
          return null;
      }
    };

    const sorted = filtered.sort((a, b) => {
      const aValue = getSortValue(a);
      const bValue = getSortValue(b);

      if (aValue == null && bValue == null) {
        return a.release_name.localeCompare(b.release_name);
      }
      if (aValue == null) {
        return 1;
      }
      if (bValue == null) {
        return -1;
      }

      if (sortOrder === 'desc') {
        const diff = bValue - aValue;
        return diff !== 0 ? diff : a.release_name.localeCompare(b.release_name);
      }

      const diff = aValue - bValue;
      return diff !== 0 ? diff : a.release_name.localeCompare(b.release_name);
    });

    return sorted;
  }, [parseSizeToBytes, searchState.results, sortField, sortOrder, sourceFilter]);

  const totalResults = searchState.results.length;
  const displayedCount = displayedResults.length;
  const summaryQuery = searchState.query || query;
  const summaryKey =
    displayedCount === totalResults
      ? 'releaseSearch.results.summary'
      : 'releaseSearch.results.summaryWithTotal';
  const summaryText = t(summaryKey, {
    count: displayedCount,
    total: totalResults,
    query: summaryQuery,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      try {
        await search(query.trim(), requestId);
      } catch (error) {
        const message = error instanceof Error ? error.message : t('releaseSearch.toasts.searchFailedFallback');
        toast({
          title: t('releaseSearch.toasts.searchFailedTitle'),
          description: message,
          status: 'error',
          duration: 4000,
          isClosable: true,
        });
      }
    }
  };

  const handleClear = () => {
    setQuery('');
    clearSearch();
    setDownloadingCandidateId(null);
    setSourceFilter('all');
  };

  const handleCandidateSelect = async (candidate: ReleaseSearchResult) => {
    setDownloadingCandidateId(candidate.release_id);
    try {
      const response = await selectReleaseCandidate(candidate, requestId);
      toast({
        title: t('releaseSearch.toasts.downloadQueuedTitle'),
        description:
          response?.message ??
          t('releaseSearch.toasts.downloadQueuedFallback', {
            name: candidate.release_name,
          }),
        status: 'success',
        duration: 4000,
        isClosable: true,
      });
      onDownloadQueued?.();
      handleClear();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : t('releaseSearch.toasts.downloadFailedFallback');
      toast({
        title: t('releaseSearch.toasts.downloadFailedTitle'),
        description: message,
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setDownloadingCandidateId(null);
    }
  };

  useEffect(() => {
    if (prefillQuery === undefined || prefillQuery === null) {
      return;
    }

    setQuery(prefillQuery.trim());
    requestAnimationFrame(() => {
      inputRef.current?.focus({ preventScroll: true });
      inputRef.current?.select();
    });
  }, [prefillQuery]);

  useEffect(() => {
    if (!focusTrigger || focusTrigger <= 0) {
      return;
    }

    requestAnimationFrame(() => {
      inputRef.current?.focus({ preventScroll: true });
      inputRef.current?.select();
    });
  }, [focusTrigger]);

  return (
    <Card p={{ base: 5, md: 6 }}>
      <Stack spacing={6}>
        <Heading size="md">{t('releaseSearch.title')}</Heading>

        <Box as="form" onSubmit={handleSubmit}>
          <Flex direction={{ base: 'column', md: 'row' }} gap={3}>
            <VisuallyHidden id="release-search-instructions">
              {t('releaseSearch.instructions')}
            </VisuallyHidden>
            <Input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('releaseSearch.placeholder', { title: requestTitle })}
              size="md"
              aria-label={t('releaseSearch.ariaLabel', { title: requestTitle })}
              aria-describedby="release-search-instructions"
            />
            <Flex gap={2}>
              <Button
                type="submit"
                isDisabled={!query.trim() || searchState.loading}
                aria-label={t('releaseSearch.actions.runSearch')}
              >
                {searchState.loading
                  ? t('releaseSearch.actions.searching')
                  : t('releaseSearch.actions.search')}
              </Button>
              {(query || searchState.results.length > 0) && (
                <Button type="button" variant="outline" colorScheme="gray" onClick={handleClear}>
                  {t('releaseSearch.actions.clear')}
                </Button>
              )}
            </Flex>
          </Flex>
        </Box>

        {searchState.loading && searchState.results.length === 0 && (
          <Stack spacing={3} role="status" aria-live="polite">
            {Array.from({ length: 3 }).map((_, index) => (
              <Stack
                key={`search-skeleton-${index}`}
                borderWidth="1px"
                borderColor="border.muted"
                borderRadius="lg"
                bg="bg.subtle"
                p={4}
                spacing={3}
              >
                <Skeleton height="16px" width="70%" borderRadius="md" />
                <SkeletonText noOfLines={2} spacing="2" skeletonHeight="12px" />
                <Skeleton height="28px" width="100px" borderRadius="full" />
              </Stack>
            ))}
          </Stack>
        )}

        {searchState.error && (
          <Alert status="error" variant="left-accent" borderRadius="lg" alignItems="flex-start">
            <AlertIcon />
            <AlertDescription>{searchState.error}</AlertDescription>
          </Alert>
        )}

        {displayedResults.length > 0 && (
          <Stack spacing={4} aria-live="polite" aria-busy={searchState.loading}>
            <Flex
              justify="space-between"
              align={{ base: 'flex-start', md: 'center' }}
              direction={{ base: 'column', md: 'row' }}
              gap={2}
            >
              <Heading size="sm">{t('releaseSearch.results.heading')}</Heading>
              <HStack spacing={2} color="text.subtle" fontSize="sm" align="center" role="status">
                <Text>{summaryText}</Text>
                {searchState.loading && searchState.results.length > 0 && (
                  <HStack spacing={1} color="text.subtle">
                    <Spinner size="xs" />
                    <Text fontSize="xs">{t('releaseSearch.results.updating')}</Text>
                  </HStack>
                )}
              </HStack>
            </Flex>

            <Flex
              direction={{ base: 'column', md: 'row' }}
              gap={3}
              align={{ base: 'stretch', md: 'flex-end' }}
            >
              <FormControl maxW={{ base: '100%', md: '220px' }}>
                <FormLabel fontSize="sm" color="text.subtle">
                  {t('releaseSearch.sort.label')}
                </FormLabel>
                <Select
                  size="sm"
                  value={sortField}
                  onChange={(event) => setSortField(event.target.value as 'seeders' | 'leechers' | 'size')}
                >
                  <option value="seeders">{t('releaseSearch.sort.fields.seeders')}</option>
                  <option value="leechers">{t('releaseSearch.sort.fields.leechers')}</option>
                  <option value="size">{t('releaseSearch.sort.fields.size')}</option>
                </Select>
              </FormControl>

              <FormControl maxW={{ base: '100%', md: '180px' }}>
                <FormLabel fontSize="sm" color="text.subtle">
                  {t('releaseSearch.sort.directionLabel')}
                </FormLabel>
                <Select
                  size="sm"
                  value={sortOrder}
                  onChange={(event) => setSortOrder(event.target.value as 'desc' | 'asc')}
                >
                  <option value="desc">{t('releaseSearch.sort.directions.desc')}</option>
                  <option value="asc">{t('releaseSearch.sort.directions.asc')}</option>
                </Select>
              </FormControl>

              {uniqueSources.length > 0 && (
                <FormControl maxW={{ base: '100%', md: '220px' }}>
                  <FormLabel fontSize="sm" color="text.subtle">
                    {t('releaseSearch.filters.source.label')}
                  </FormLabel>
                  <Select
                    size="sm"
                    value={sourceFilter}
                    onChange={(event) => setSourceFilter(event.target.value)}
                  >
                    <option value="all">{t('releaseSearch.filters.source.all')}</option>
                    {uniqueSources.map((source) => (
                      <option key={source} value={source}>
                        {source}
                      </option>
                    ))}
                  </Select>
                </FormControl>
              )}
            </Flex>

            <Stack spacing={3}>
              {displayedResults.map((candidate) => {
                const qualityLabel = candidate.quality ?? t('releaseSearch.quality.unknown');
                const qualityColor = qualityColorScheme[qualityLabel] || 'gray';
                const seedersLabel = candidate.seeders ?? 0;
                const leechersLabel = candidate.leechers ?? 0;
                return (
                  <Flex
                    key={candidate.release_id}
                    direction={{ base: 'column', md: 'row' }}
                    justify="space-between"
                    align={{ base: 'flex-start', md: 'center' }}
                    gap={4}
                    p={4}
                    borderWidth="1px"
                    borderColor="border.muted"
                    borderRadius="lg"
                    bg="bg.subtle"
                  >
                    <Stack spacing={2} flex={1} minW={0}>
                      <Text fontWeight="600" fontSize="sm" color="slate.100" noOfLines={2}>
                        {candidate.release_name}
                      </Text>
                      <Flex gap={3} wrap="wrap" fontSize="xs" color="text.subtle">
                        <Tag
                          colorScheme={qualityColor}
                          variant="subtle"
                          borderRadius="full"
                          px={3}
                          py={1}
                        >
                          {qualityLabel}
                        </Tag>
                        <Text>📦 {candidate.size}</Text>
                        <Text color="green.300">⬆️ {seedersLabel}</Text>
                        <Text color="red.300">⬇️ {leechersLabel}</Text>
                        {candidate.source && <Text>🏷️ {candidate.source}</Text>}
                        {candidate.magnet_link && (
                          <Button
                            as="a"
                            href={candidate.magnet_link}
                            target="_self"
                            rel="noopener noreferrer"
                            size="xs"
                            variant="link"
                            colorScheme="orange"
                            px={0}
                          >
                            {t('releaseSearch.links.magnet')}
                          </Button>
                        )}
                        {candidate.info_url && (
                          <Button
                            as="a"
                            href={candidate.info_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="xs"
                            variant="link"
                            colorScheme="blue"
                            px={0}
                          >
                            {t('releaseSearch.links.info')}
                          </Button>
                        )}
                        {candidate.torrent_file_url && (
                          <Button
                            as="a"
                            href={candidate.torrent_file_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="xs"
                            variant="link"
                            colorScheme="green"
                            px={0}
                          >
                            {t('releaseSearch.links.torrent')}
                          </Button>
                        )}
                      </Flex>
                    </Stack>

                    <Button
                      onClick={() => handleCandidateSelect(candidate)}
                      size="sm"
                      isLoading={downloadingCandidateId === candidate.release_id}
                      loadingText={t('releaseSearch.loading.queueing')}
                      isDisabled={
                        !!downloadingCandidateId && downloadingCandidateId !== candidate.release_id
                      }
                      aria-label={t('releaseSearch.actions.queueDownload', {
                        name: candidate.release_name,
                      })}
                    >
                      {t('releaseSearch.download')}
                    </Button>
                  </Flex>
                );
              })}
            </Stack>
          </Stack>
        )}

        {searchState.query &&
          displayedResults.length === 0 &&
          !searchState.loading &&
          !searchState.error && (
            <Stack
              spacing={3}
              py={10}
              align="center"
              borderWidth="1px"
              borderColor="border.muted"
              borderRadius="xl"
              bg="bg.subtle"
            >
              <Text fontSize="4xl">🔍</Text>
              <Heading size="sm">{t('releaseSearch.empty.title')}</Heading>
              <Text color="text.subtle" fontSize="sm" textAlign="center" px={6}>
                {t('releaseSearch.empty.description')}
              </Text>
            </Stack>
          )}
      </Stack>
    </Card>
  );
};
