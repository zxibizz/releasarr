import { Badge, Group, Paper, Skeleton, Stack, Table, Text, Title } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { useRequestEpisodes } from '@/features/requests/queries';
import type { EpisodeStatus, SeasonEpisode } from '@/types';
import { formatDate, formatFileSize } from '@/utils/formatters';

const STATUS_COLORS: Record<EpisodeStatus, string> = {
  downloaded: 'teal',
  missing: 'yellow',
  unaired: 'gray',
};

const NOWRAP = { whiteSpace: 'nowrap' } as const;

// A badge hides its label's overflow, which as a grid item lets the label
// shrink to nothing: the label stops asking for the width of its own text, the
// column it sits in inherits that, and the label comes out as an ellipsis.
// Showing the overflow restores the ask, so the badge can never be narrower
// than what it says.
const BADGE_STYLES = { label: { overflow: 'visible' } } as const;

interface SeasonEpisodesProps {
  requestId: string;
}

/**
 * What the requested season is made of, and how much of it has arrived.
 *
 * Nothing is rendered when the episodes cannot be had: a request the Sonarr
 * sync has not linked to a series yet is answered with a conflict rather than a
 * list, and that is the ordinary state of a request for its first few minutes.
 * An alert for it would fire on a page whose own content is fine, so the table
 * simply waits until there is something to show.
 */
export function SeasonEpisodes({ requestId }: SeasonEpisodesProps) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useRequestEpisodes(requestId);

  const episodes = data?.episodes ?? [];
  const downloaded = episodes.filter((episode) => episode.status === 'downloaded').length;
  const onDisk = episodes.reduce((total, episode) => total + (episode.file_size ?? 0), 0);

  if (isLoading) {
    return (
      <Stack gap="md">
        <Skeleton height={24} width={180} />
        <Skeleton height={120} radius="lg" />
      </Stack>
    );
  }

  if (error || episodes.length === 0) {
    return null;
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="baseline" wrap="nowrap" gap="sm">
        <Title order={3}>{t('requestPage.episodes.title')}</Title>
        <Text size="sm" c="dimmed">
          {t('requestPage.episodes.summary', { downloaded, total: episodes.length })}
          {onDisk > 0 && ` · ${t('requestPage.episodes.onDisk', { size: formatFileSize(onDisk) })}`}
        </Text>
      </Group>

      <Paper withBorder radius="lg" p={0}>
        <Table.ScrollContainer minWidth={520}>
          <Table verticalSpacing="xs" horizontalSpacing="md" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={56}>{t('requestPage.episodes.columns.number')}</Table.Th>
                {/* The title takes what the others leave, so each of those sits
                    at the width of its own content. Pinning them to a fixed
                    width instead is what cuts a label short, and the longest of
                    these labels is not the English one. */}
                <Table.Th style={{ width: '100%' }}>
                  {t('requestPage.episodes.columns.title')}
                </Table.Th>
                <Table.Th style={NOWRAP}>{t('requestPage.episodes.columns.airDate')}</Table.Th>
                <Table.Th style={NOWRAP}>{t('requestPage.episodes.columns.status')}</Table.Th>
                <Table.Th style={NOWRAP}>{t('requestPage.episodes.columns.size')}</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {episodes.map((episode) => (
                <EpisodeRow key={episode.episode_number} episode={episode} />
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Paper>
    </Stack>
  );
}

function EpisodeRow({ episode }: { episode: SeasonEpisode }) {
  const { t } = useTranslation();

  return (
    <Table.Tr>
      <Table.Td>
        <Text size="sm" c="dimmed" ff="monospace">
          {episode.episode_number}
        </Text>
      </Table.Td>
      <Table.Td>
        <Text size="sm">{episode.title || t('requestPage.episodes.untitled')}</Text>
      </Table.Td>
      <Table.Td style={NOWRAP}>
        <Text size="sm" c="dimmed">
          {episode.air_date ? formatDate(episode.air_date) : t('requestPage.episodes.notScheduled')}
        </Text>
      </Table.Td>
      <Table.Td style={NOWRAP}>
        <Badge
          color={STATUS_COLORS[episode.status]}
          variant="light"
          radius="sm"
          styles={BADGE_STYLES}
        >
          {t(`requestPage.episodes.status.${episode.status}`)}
        </Badge>
      </Table.Td>
      <Table.Td style={NOWRAP}>
        <Text size="sm" c="dimmed">
          {episode.file_size ? formatFileSize(episode.file_size) : '—'}
        </Text>
      </Table.Td>
    </Table.Tr>
  );
}
