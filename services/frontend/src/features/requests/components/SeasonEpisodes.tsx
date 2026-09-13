import { Badge, Divider, Group, Paper, Skeleton, Stack, Table, Text, Title } from '@mantine/core';
import { Fragment } from 'react';
import { useTranslation } from 'react-i18next';

import { seasonLabelKey } from '@/features/discover/seasons';
import { useRequestEpisodes } from '@/features/requests/queries';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { EpisodeStatus, SeasonEpisode } from '@/types';
import { formatDate, formatFileSize } from '@/utils/formatters';
import { EPISODE_STATUS_COLOR } from '@/utils/status';

const STATUS_COLORS: Record<EpisodeStatus, string> = EPISODE_STATUS_COLOR;

const NOWRAP = { whiteSpace: 'nowrap' } as const;

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
  const isMobile = useIsMobile();
  const { data, isLoading, error } = useRequestEpisodes(requestId);

  const episodes = data?.episodes ?? [];
  const seasonNumber = data?.season_number ?? 0;
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
      <Group justify="space-between" align="baseline" gap="sm">
        {/* Which season these are: the page heading names the series, and a
            series can have a request open for several of its seasons. Beside
            the heading rather than inside it, which read as a sentence about
            the season instead of a name for the section. */}
        <Group gap="sm" align="center" wrap="nowrap">
          <Title order={3}>{t('requestPage.episodes.title')}</Title>
          <Badge variant="default" radius="sm">
            {t(seasonLabelKey(seasonNumber), { season: seasonNumber })}
          </Badge>
        </Group>
        <Text size="sm" c="dimmed">
          {t('requestPage.episodes.summary', { downloaded, total: episodes.length })}
          {onDisk > 0 && ` · ${t('requestPage.episodes.onDisk', { size: formatFileSize(onDisk) })}`}
        </Text>
      </Group>

      <Paper withBorder radius="lg" p={0}>
        {isMobile ? <EpisodeList episodes={episodes} /> : <EpisodeTable episodes={episodes} />}
      </Paper>
    </Stack>
  );
}

function EpisodeTable({ episodes }: { episodes: SeasonEpisode[] }) {
  const { t } = useTranslation();

  return (
    <Table.ScrollContainer minWidth={520}>
      <Table verticalSpacing="xs" horizontalSpacing="md" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={56}>{t('requestPage.episodes.columns.number')}</Table.Th>
            {/* The title takes what the others leave, so each of those sits at
                the width of its own content. Pinning them to a fixed width
                instead is what cuts a label short, and the longest of these
                labels is not the English one. */}
            <Table.Th style={{ width: '100%' }}>{t('requestPage.episodes.columns.title')}</Table.Th>
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
        <StatusBadge status={episode.status} />
      </Table.Td>
      <Table.Td style={NOWRAP}>
        <Text size="sm" c="dimmed">
          {episode.file_size ? formatFileSize(episode.file_size) : '—'}
        </Text>
      </Table.Td>
    </Table.Tr>
  );
}

/**
 * The same episodes two lines to a row, for a phone.
 *
 * Five columns have no chance of fitting one: the cell padding alone claims
 * most of the width, and what is left has to cover a date, a size and a status
 * badge before the title gets any. Folding the date and size onto a second line
 * hands the title the whole of the first, and costs only height.
 */
function EpisodeList({ episodes }: { episodes: SeasonEpisode[] }) {
  return (
    <Stack gap={0}>
      {episodes.map((episode, index) => (
        <Fragment key={episode.episode_number}>
          {index > 0 && <Divider />}
          <EpisodeListRow episode={episode} />
        </Fragment>
      ))}
    </Stack>
  );
}

function EpisodeListRow({ episode }: { episode: SeasonEpisode }) {
  const { t } = useTranslation();

  const meta = [
    episode.air_date ? formatDate(episode.air_date) : t('requestPage.episodes.notScheduled'),
    episode.file_size ? formatFileSize(episode.file_size) : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm" px="md" py="sm">
      <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
        <Text size="sm" className="break-anywhere">
          {episode.episode_number}. {episode.title || t('requestPage.episodes.untitled')}
        </Text>
        <Text size="xs" c="dimmed">
          {meta}
        </Text>
      </Stack>
      <StatusBadge status={episode.status} />
    </Group>
  );
}

function StatusBadge({ status }: { status: EpisodeStatus }) {
  const { t } = useTranslation();

  return (
    <Badge
      color={STATUS_COLORS[status]}
      variant="light"
      radius="sm"
      // A badge hides its label's overflow, which as a grid item lets the label
      // shrink to nothing: the label stops asking for the width of its own
      // text, whatever holds it inherits that, and the label comes out as an
      // ellipsis. Showing the overflow restores the ask, so the badge is never
      // narrower than what it says.
      styles={{ label: { overflow: 'visible' } }}
    >
      {t(`requestPage.episodes.status.${status}`)}
    </Badge>
  );
}
