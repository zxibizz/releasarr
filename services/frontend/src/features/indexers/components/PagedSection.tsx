import { Alert, Button, Group, Loader, Skeleton, Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { Panel } from '@/components/Panel';
import { getErrorMessage } from '@/utils/errors';

interface PagedSectionProps {
  /**
   * Prefix of the translation keys for this section, which must define
   * `error.title`, `error.description`, `empty.*`, `previous`, `next` and
   * `pageStatus`. Both sections of the indexer logs modal have the same shape.
   */
  i18nBase: string;
  filters: ReactNode;
  loading: boolean;
  fetching: boolean;
  error: unknown;
  onRetry: () => void;
  isEmpty: boolean;
  /** Changes the empty text from "nothing yet" to "nothing matched". */
  isFiltered: boolean;
  page: number;
  lastPage: number;
  total: number;
  onPageChange: (page: number) => void;
  children: ReactNode;
}

/**
 * The frame both tabs of the indexer logs modal share: filters, a paged table,
 * and the states that replace it while it has nothing to show.
 */
export function PagedSection({
  i18nBase,
  filters,
  loading,
  fetching,
  error,
  onRetry,
  isEmpty,
  isFiltered,
  page,
  lastPage,
  total,
  onPageChange,
  children,
}: PagedSectionProps) {
  const { t } = useTranslation();

  return (
    <Stack gap="sm">
      <Group gap="sm" align="flex-end" wrap="wrap">
        {filters}
        {fetching && <Loader size="xs" mb={8} />}
      </Group>

      {Boolean(error) && (
        <Alert color="red" radius="lg" title={t(`${i18nBase}.error.title`)}>
          <Stack align="flex-start" gap="sm">
            <Text>{getErrorMessage(error, t(`${i18nBase}.error.description`))}</Text>
            <Button variant="light" size="xs" onClick={onRetry}>
              {t('common.tryAgain')}
            </Button>
          </Stack>
        </Alert>
      )}

      {loading ? (
        <Stack gap="sm">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} height={24} radius="sm" />
          ))}
        </Stack>
      ) : isEmpty ? (
        !error && (
          <EmptyState
            icon="📋"
            title={t(`${i18nBase}.empty.title`)}
            description={
              isFiltered ? t(`${i18nBase}.empty.filtered`) : t(`${i18nBase}.empty.description`)
            }
          />
        )
      ) : (
        <Panel>{children}</Panel>
      )}

      {total > 0 && (
        <Group justify="space-between" align="center">
          <Text size="sm" c="dimmed">
            {t(`${i18nBase}.pageStatus`, { page, lastPage, total })}
          </Text>
          <Group gap="xs">
            <Button
              size="xs"
              variant="default"
              disabled={page <= 1}
              onClick={() => onPageChange(Math.max(1, page - 1))}
            >
              {t(`${i18nBase}.previous`)}
            </Button>
            <Button
              size="xs"
              variant="default"
              disabled={page >= lastPage}
              onClick={() => onPageChange(page + 1)}
            >
              {t(`${i18nBase}.next`)}
            </Button>
          </Group>
        </Group>
      )}
    </Stack>
  );
}
