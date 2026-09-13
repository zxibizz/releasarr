import { Badge, Group, Paper, Skeleton, Stack, Table, Text, Title } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { useRequestEpisodes } from '@/features/requests/queries';
import type { EpisodeStatus, SeasonEpisode } from '@/types';
import { formatDate } from '@/utils/formatters';

const STATUS_COLORS: Record<EpisodeStatus, string> = {
  downloaded: 'teal',
  missing: 'yellow',
  unaired: 'gray',
};

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
        </Text>
      </Group>

      <Paper withBorder radius="lg" p={0}>
        {/* The title column is the one that needs room, so the scroll floor is
            set wide enough for the other three to stay side by side. */}
        <Table.ScrollContainer minWidth={420}>
          <Table verticalSpacing="xs" horizontalSpacing="md" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={60}>{t('requestPage.episodes.columns.number')}</Table.Th>
                <Table.Th>{t('requestPage.episodes.columns.title')}</Table.Th>
                <Table.Th w={140}>{t('requestPage.episodes.columns.airDate')}</Table.Th>
                <Table.Th w={140}>{t('requestPage.episodes.columns.status')}</Table.Th>
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
      <Table.Td>
        <Text size="sm" c="dimmed">
          {episode.air_date ? formatDate(episode.air_date) : t('requestPage.episodes.notScheduled')}
        </Text>
      </Table.Td>
      <Table.Td>
        <Badge color={STATUS_COLORS[episode.status]} variant="light" radius="sm">
          {t(`requestPage.episodes.status.${episode.status}`)}
        </Badge>
      </Table.Td>
    </Table.Tr>
  );
}
