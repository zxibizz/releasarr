import { Badge, Card, Group, Image, Stack, Text, Title } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { StatusBadge } from '@/components/StatusBadge';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { MediaRequest } from '@/types';
import { formatDate, formatRuntime } from '@/utils/formatters';

interface RequestCardProps {
  request: MediaRequest;
}

export function RequestCard({ request }: RequestCardProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const isMovie = request.type === 'movie';

  const subtitle = isMovie
    ? formatRuntime(request.runtime)
    : t('requestCard.season', { season: request.season_number });

  return (
    <Card
      withBorder
      radius="lg"
      padding="lg"
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

          <Text size="xs" c="dimmed" mt="auto">
            {t('requestCard.createdAt', { date: formatDate(request.created_at) })}
          </Text>
        </Stack>
      </Group>
    </Card>
  );
}
