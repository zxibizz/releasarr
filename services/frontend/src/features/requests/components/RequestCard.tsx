import { Badge, Card, Group, Image, Stack, Text, Title } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { StatusBadge } from '@/components/StatusBadge';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { MediaRequest } from '@/types';
import { formatDate, formatRuntime } from '@/utils/formatters';
import { EPISODE_STATUS_COLOR, WARNING_COLOR } from '@/utils/status';

interface RequestCardProps {
  request: MediaRequest;
}

export function RequestCard({ request }: RequestCardProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const isMovie = request.type === 'movie';
  const warningCount = request.warnings?.length ?? 0;

  const subtitle = isMovie
    ? formatRuntime(request.runtime)
    : t('requestCard.season', { season: request.season_number });

  /*
    The card is a summary, so each bucket collapses to an emoji and a number;
    the full breakdown lives on the detail page. Zero-count buckets are dropped
    rather than rendered as "0", which is what made the row wide in the first
    place. The localized label is carried as the accessible name, since neither
    the emoji nor the bare number says anything on its own.
  */
  const episodeItems =
    request.type === 'series' && request.episode_counts
      ? (
          [
            ['downloaded', '✅', request.episode_counts.downloaded],
            ['pending', '⏳', request.episode_counts.pending],
            ['unaired', '◻️', request.episode_counts.unaired],
          ] as const
        )
          .filter(([, , count]) => count > 0)
          .map(([key, emoji, count]) => ({
            key,
            emoji,
            count,
            color: EPISODE_STATUS_COLOR[key],
            label: t(`requestCard.episodes.${key}`, { count }),
          }))
      : [];
  const episodeSummary = episodeItems.map((item) => item.label).join(', ');

  /*
    Null until something is exported, which is also when the line goes away.
  */
  const exportedLabel = request.exported_at
    ? t('requestCard.exported', { date: formatDate(request.exported_at) })
    : null;

  return (
    <Card
      withBorder
      radius="lg"
      padding={isMobile ? 'sm' : 'lg'}
      component={Link}
      to={`/request/${request.id}`}
      style={{ height: '100%', textDecoration: 'none' }}
    >
      <Group align="flex-start" wrap="nowrap" gap="md" h="100%">
        {/*
          The poster is the fastest way to recognise a request, so it stays on a
          phone too — just narrow enough to leave the text a readable column.
        */}
        <Image
          src={request.poster_url}
          alt={t('requestCard.posterAlt', { title: request.title })}
          w={{ base: 72, sm: 110 }}
          h={{ base: 108, sm: 165 }}
          radius="md"
          fit="cover"
          loading="lazy"
          fallbackSrc="https://placehold.co/110x165?text=No+Poster"
          style={{ flexShrink: 0 }}
        />

        <Stack gap="xs" style={{ flex: 1, minWidth: 0 }} h="100%">
          <div>
            <Title order={4} lineClamp={2}>
              {request.title}
            </Title>
            <Text size="sm" c="dimmed">
              {request.year} • {subtitle}
            </Text>
          </div>

          {/*
            Genres and the synopsis are browsing detail, not identifying detail:
            on a phone they tripled the height of every card and pushed the list
            itself off screen. The poster, title and status are what a request is
            recognised by, so only those survive the narrow layout.
          */}
          <Group gap="xs">
            <StatusBadge status={request.status} />
            {warningCount > 0 && (
              <Badge
                color={WARNING_COLOR}
                variant="light"
                radius="sm"
                aria-label={t('requestCard.warnings', { count: warningCount })}
                title={t('requestCard.warnings', { count: warningCount })}
              >
                ⚠️ {warningCount}
              </Badge>
            )}
            <Badge color={isMovie ? 'red' : 'blue'} variant="light" radius="sm">
              {isMovie ? '🎬' : '📺'} {t(`mediaType.${request.type}`)}
            </Badge>
            {!isMobile &&
              request.genres.slice(0, 2).map((genre) => (
                <Badge key={genre} color="gray" variant="default" radius="sm">
                  {genre}
                </Badge>
              ))}
            {!isMobile && request.genres.length > 2 && (
              <Badge color="gray" variant="default" radius="sm">
                +{request.genres.length - 2}
              </Badge>
            )}
          </Group>

          {!isMobile && (
            <Text size="sm" c="gray.4" lineClamp={3}>
              {request.overview}
            </Text>
          )}

          {/*
            The footer pairs the two facts that answer "where is this up to":
            when it last reached the arr, and how much of the season came with
            it. `mt="auto"` keeps it on the baseline so a row of cards lines up
            whether or not either fact exists yet.
          */}
          {exportedLabel !== null || episodeItems.length > 0 ? (
            <Group
              justify={exportedLabel ? 'space-between' : 'flex-end'}
              align="center"
              gap="sm"
              wrap="nowrap"
              mt="auto"
            >
              {exportedLabel && (
                // Yields space before the counts do, since the counts are the
                // part that cannot be guessed from the rest of the card.
                <Text
                  size="xs"
                  c="dimmed"
                  aria-label={exportedLabel}
                  title={exportedLabel}
                  style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}
                >
                  {exportedLabel}
                </Text>
              )}
              {episodeItems.length > 0 &&
                (isMobile ? (
                  <Text
                    size="xs"
                    c="dimmed"
                    aria-label={episodeSummary}
                    title={episodeSummary}
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    {episodeItems.map((item) => `${item.emoji} ${item.count}`).join(' · ')}
                  </Text>
                ) : (
                  <Group gap={4} style={{ flexShrink: 0 }}>
                    {episodeItems.map((item) => (
                      <Badge
                        key={item.key}
                        size="xs"
                        color={item.color}
                        variant="light"
                        radius="sm"
                        px={6}
                        aria-label={item.label}
                        title={item.label}
                      >
                        {item.emoji} {item.count}
                      </Badge>
                    ))}
                  </Group>
                ))}
            </Group>
          ) : (
            <div style={{ marginTop: 'auto' }} />
          )}
        </Stack>
      </Group>
    </Card>
  );
}
