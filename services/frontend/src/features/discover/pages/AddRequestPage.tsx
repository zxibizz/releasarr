import {
  Alert,
  Button,
  Group,
  Paper,
  SimpleGrid,
  Skeleton,
  Stack,
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

  const search = useMediaSearch(submitted);
  const results = search.data?.results ?? [];

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
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
            {results.map((result) => (
              <MediaSearchResultCard
                key={`${result.type}-${result.provider_id}`}
                result={result}
                onPick={setPicked}
              />
            ))}
          </SimpleGrid>
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
