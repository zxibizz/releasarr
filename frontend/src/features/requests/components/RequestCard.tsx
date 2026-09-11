import { Badge, Card, Group, Image, Stack, Text, Title } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { StatusBadge } from '@/components/StatusBadge';
import type { MediaRequest } from '@/types';
import { formatDate, formatRuntime } from '@/utils/formatters';

interface RequestCardProps {
  request: MediaRequest;
}

export function RequestCard({ request }: RequestCardProps) {
  const { t } = useTranslation();
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
        <Image
          src={request.poster_url}
          alt={t('requestCard.posterAlt', { title: request.title })}
          w={110}
          h={165}
          radius="md"
          fit="cover"
          visibleFrom="sm"
          fallbackSrc="https://placehold.co/110x165?text=No+Poster"
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

          <Group gap="xs">
            <StatusBadge status={request.status} />
            <Badge color={isMovie ? 'red' : 'blue'} variant="light" radius="sm">
              {isMovie ? '🎬' : '📺'} {t(`mediaType.${request.type}`)}
            </Badge>
            {request.genres.slice(0, 2).map((genre) => (
              <Badge key={genre} color="gray" variant="default" radius="sm">
                {genre}
              </Badge>
            ))}
            {request.genres.length > 2 && (
              <Badge color="gray" variant="default" radius="sm">
                +{request.genres.length - 2}
              </Badge>
            )}
          </Group>

          <Text size="sm" c="gray.4" lineClamp={3}>
            {request.overview}
          </Text>

          <Text size="xs" c="dimmed" mt="auto">
            {t('requestCard.createdAt', { date: formatDate(request.created_at) })}
          </Text>
        </Stack>
      </Group>
    </Card>
  );
}
