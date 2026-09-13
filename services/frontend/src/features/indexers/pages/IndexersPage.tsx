import { Alert, Button, Group, Loader, Skeleton, Stack, Text, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconListDetails, IconPlugConnected } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { Panel } from '@/components/Panel';
import { IndexerLogsModal } from '@/features/indexers/components/IndexerLogsModal';
import { IndexersTable } from '@/features/indexers/components/IndexersTable';
import { isIndexerUnhealthy, useIndexers, useTestAllIndexers } from '@/features/indexers/queries';
import { ApiError } from '@/lib/api/client';
import { getErrorMessage } from '@/utils/errors';

export function IndexersPage() {
  const { t } = useTranslation();
  const indexers = useIndexers();
  const testAll = useTestAllIndexers();
  const [logsOpened, logsModal] = useDisclosure(false);

  const list = indexers.data ?? [];
  const unhealthy = list.filter(isIndexerUnhealthy);
  const notConfigured = indexers.error instanceof ApiError && indexers.error.status === 503;

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <Stack gap={4}>
          <Title order={1}>{t('indexers.page.title')}</Title>
          <Text c="dimmed">{t('indexers.page.subtitle')}</Text>
        </Stack>

        <Group gap="sm">
          {indexers.isFetching && <Loader size="xs" />}
          <Button
            size="sm"
            variant="default"
            leftSection={<IconListDetails size={16} />}
            disabled={notConfigured}
            onClick={logsModal.open}
          >
            {t('indexers.page.logs')}
          </Button>
          <Button
            size="sm"
            variant="light"
            leftSection={<IconPlugConnected size={16} />}
            loading={testAll.isPending}
            disabled={notConfigured}
            onClick={() => testAll.mutate()}
          >
            {t('indexers.page.testAll')}
          </Button>
        </Group>
      </Group>

      {notConfigured ? (
        <Alert color="yellow" radius="lg" title={t('indexers.page.notConfigured.title')}>
          {t('indexers.page.notConfigured.description')}
        </Alert>
      ) : (
        indexers.error && (
          <Alert color="red" radius="lg" title={t('indexers.page.error.title')}>
            <Stack align="flex-start" gap="sm">
              <Text>{getErrorMessage(indexers.error, t('indexers.page.error.description'))}</Text>
              <Button variant="light" size="xs" onClick={() => void indexers.refetch()}>
                {t('common.tryAgain')}
              </Button>
            </Stack>
          </Alert>
        )
      )}

      {unhealthy.length > 0 && (
        <Alert color="yellow" radius="lg" title={t('indexers.page.unhealthy.title')}>
          {t('indexers.page.unhealthy.description', {
            count: unhealthy.length,
            names: unhealthy.map((indexer) => indexer.name).join(', '),
          })}
        </Alert>
      )}

      <Panel>
        {indexers.isLoading ? (
          <TableSkeleton rows={4} />
        ) : list.length === 0 && !indexers.error ? (
          <EmptyState
            icon="📡"
            title={t('indexers.page.empty.title')}
            description={t('indexers.page.empty.description')}
          />
        ) : (
          <IndexersTable indexers={list} />
        )}
      </Panel>

      <IndexerLogsModal indexers={list} opened={logsOpened} onClose={logsModal.close} />
    </Stack>
  );
}

function TableSkeleton({ rows }: { rows: number }) {
  return (
    <Stack gap="sm" p="md">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} height={32} radius="sm" />
      ))}
    </Stack>
  );
}
