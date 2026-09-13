import { Badge, Button, Card, Group, Image, Stack, Text, Title } from '@mantine/core';
import { IconListCheck } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { StatusBadge } from '@/components/StatusBadge';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { MediaRequest } from '@/types';
import { formatRuntime } from '@/utils/formatters';

interface MediaInfoProps {
  request: MediaRequest;
  /** Offers the way in to managing the series' seasons, for a series request. */
  onManageSeasons?: () => void;
}

export function MediaInfo({ request, onManageSeasons }: MediaInfoProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const isMovie = request.type === 'movie';

  const poster = (
    <Image
      src={request.poster_url}
      alt={t('requestCard.posterAlt', { title: request.title })}
      w={{ base: 84, md: 240 }}
      h={{ base: 126, md: 360 }}
      radius="md"
      fit="cover"
      fallbackSrc="https://placehold.co/240x360?text=No+Poster"
      style={{ flexShrink: 0 }}
    />
  );

  /*
   * Everything the card used to spread across a grid of bordered tiles. Each
   * value was three words at most, and a caption above it said what a reader
   * could already tell — a year looks like a year. The two dates the grid also
   * carried are gone rather than moved: neither answers a question the page is
   * asked.
   */
  const meta = [
    isMovie ? `🎬 ${t('mediaType.movie')}` : `📺 ${t('mediaType.series')}`,
    String(request.year),
    isMovie
      ? formatRuntime(request.runtime)
      : t('requestCard.season', { season: request.season_number }),
    isMovie ? null : t('mediaInfo.episodes', { count: request.total_episodes }),
  ]
    .filter(Boolean)
    .join(' · ');

  /*
   * Sonarr's own name for the series, which the heading is only missing when it
   * is showing a translation of it instead. A line of its own rather than a
   * segment of the meta line: it is a name among counts, and long enough to
   * wrap on its own terms.
   */
  const originalTitle =
    !isMovie && !request.title.includes(request.series_title) ? request.series_title : null;

  /*
   * Beside the poster the title gets barely half the screen, and a localised
   * title is often one unbreakable word longer than that — at `h2` it ran past
   * the card edge. A step down in size plus a mid-word wrap keeps every title
   * whole, whatever language it came back in.
   */
  const titleBlock = (
    <Stack gap={6} style={{ flex: 1, minWidth: 0 }}>
      <Title order={isMobile ? 3 : 2} className="break-anywhere">
        {request.title}
      </Title>
      {/*
        One wrapping line rather than a row of separate values, so the narrow
        column beside the poster reflows it instead of overflowing. Kept close
        to body text in size and brightness: this is what the card is for, and
        at the dimmed `sm` a subtitle would take it read as a caption.
      */}
      <Text fz={{ base: 'sm', md: 'md' }} fw={500} c="gray.3">
        {meta}
      </Text>
      {originalTitle && (
        <Text size="sm" c="dimmed" className="break-anywhere">
          {originalTitle}
        </Text>
      )}
    </Stack>
  );

  const controls = (
    <Group gap="sm" wrap="nowrap">
      {onManageSeasons && (
        <Button
          variant="light"
          size={isMobile ? 'compact-sm' : 'xs'}
          leftSection={<IconListCheck size={16} />}
          onClick={onManageSeasons}
        >
          {t('requestPage.seasons.manage')}
        </Button>
      )}
      <StatusBadge status={request.status} size={isMobile ? 'md' : 'lg'} />
    </Group>
  );

  const details = (
    <>
      {request.genres.length > 0 && (
        <Stack gap="xs">
          <Title order={5}>{t('mediaInfo.sections.genres')}</Title>
          <Group gap="xs">
            {request.genres.map((genre) => (
              <Badge key={genre} variant="default" radius="xl">
                {genre}
              </Badge>
            ))}
          </Group>
        </Stack>
      )}

      <Stack gap="xs">
        <Title order={5}>{t('mediaInfo.sections.overview')}</Title>
        <Text size="sm" c="gray.4">
          {request.overview}
        </Text>
      </Stack>
    </>
  );

  /*
   * A phone cannot fit the poster beside the details, so only the title sits
   * next to it and everything else spans the full width underneath. The season
   * button and status take a row of their own rather than wrapping inside the
   * narrow column left over next to the poster.
   */
  if (isMobile) {
    return (
      <Card withBorder radius="lg" padding="sm">
        <Stack gap="md">
          <Group align="flex-start" gap="sm" wrap="nowrap">
            {poster}
            {titleBlock}
          </Group>
          {controls}
          {details}
        </Stack>
      </Card>
    );
  }

  return (
    <Card withBorder radius="lg" padding="lg">
      <Group align="flex-start" gap="xl" wrap="nowrap">
        {poster}
        <Stack gap="lg" style={{ flex: 1, minWidth: 0 }}>
          <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
            {titleBlock}
            {controls}
          </Group>
          {details}
        </Stack>
      </Group>
    </Card>
  );
}
