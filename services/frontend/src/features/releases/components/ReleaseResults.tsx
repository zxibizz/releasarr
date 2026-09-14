import { Anchor, Badge, Button, Group, Paper, Stack, Text } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { ageInDays } from '@/features/releases/useReleaseSearch';
import type { ReleaseSearchResult } from '@/types';
import { formatDateTime } from '@/utils/formatters';
import { QUALITY_COLOR } from '@/utils/status';

interface ReleaseResultsProps {
  results: ReleaseSearchResult[];
  downloadingId: string | null;
  setDownloadingId: (releaseId: string | null) => void;
  download: { mutate: (candidate: ReleaseSearchResult) => void };
}

export function ReleaseResults({
  results,
  downloadingId,
  setDownloadingId,
  download,
}: ReleaseResultsProps) {
  const { t } = useTranslation();

  const ageLabel = (days: number | null): string => {
    if (days === null) return t('releaseSearch.age.unknown');
    if (days < 1) return t('releaseSearch.age.today');
    return t('releaseSearch.age.days', { count: Math.floor(days) });
  };

  return (
    <Stack gap="sm">
      {results.map((candidate) => {
        const quality = candidate.quality;
        const age = ageInDays(candidate);
        const publishedAt = candidate.publish_date
          ? formatDateTime(candidate.publish_date)
          : null;
        return (
          <Paper key={candidate.release_id} withBorder radius="md" p={{ base: 'sm', sm: 'md' }}>
            <Group justify="space-between" align="center" wrap="wrap" gap="md">
              <Stack gap={6} style={{ flex: '1 1 240px', minWidth: 0 }}>
                <Text size="sm" fw={600} className="break-anywhere">
                  {candidate.release_name}
                </Text>
                <Group gap="sm" fz="xs" c="dimmed" wrap="wrap">
                  {quality && (
                    <Badge size="sm" radius="xl" variant="light" color={QUALITY_COLOR[quality] ?? 'gray'}>
                      {quality}
                    </Badge>
                  )}
                  <Text size="xs" title={publishedAt ?? undefined}>
                    🕒 {ageLabel(age)}
                  </Text>
                  <Text size="xs">📦 {candidate.size}</Text>
                  <Text size="xs" c="teal">
                    ⬆️ {candidate.seeders ?? 0}
                  </Text>
                  <Text size="xs" c="red">
                    ⬇️ {candidate.leechers ?? 0}
                  </Text>
                  {candidate.source && <Text size="xs">🏷️ {candidate.source}</Text>}
                  {candidate.info_url && (
                    <Anchor
                      href={candidate.info_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      size="xs"
                    >
                      {t('releaseSearch.links.info')}
                    </Anchor>
                  )}
                </Group>
              </Stack>

              <Button
                size="xs"
                w={{ base: '100%', sm: 'auto' }}
                loading={downloadingId === candidate.release_id}
                disabled={Boolean(downloadingId) && downloadingId !== candidate.release_id}
                aria-label={t('releaseSearch.actions.queueDownload', {
                  name: candidate.release_name,
                })}
                onClick={() => {
                  setDownloadingId(candidate.release_id);
                  download.mutate(candidate);
                }}
              >
                {t('releaseSearch.download')}
              </Button>
            </Group>
          </Paper>
        );
      })}
    </Stack>
  );
}
