import { Badge, Card, Group, Image, Paper, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { StatusBadge } from '@/components/StatusBadge';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { MediaRequest } from '@/types';
import { formatDate, formatRuntime } from '@/utils/formatters';

interface MediaInfoProps {
  request: MediaRequest;
  languageSelector?: ReactNode;
}

function InfoItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Paper withBorder radius="md" p="sm">
      <Text size="xs" c="dimmed" tt="uppercase">
        {label}
      </Text>
      <Text size="sm" fw={600} mt={4}>
        {children}
      </Text>
    </Paper>
  );
}

export function MediaInfo({ request, languageSelector }: MediaInfoProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const isMovie = request.type === 'movie';

  const poster = (
    <Image
      src={request.poster_url}
      alt={t('requestCard.posterAlt', { title: request.title })}
      w={{ base: 100, md: 240 }}
      h={{ base: 150, md: 360 }}
      radius="md"
      fit="cover"
      fallbackSrc="https://placehold.co/240x360?text=No+Poster"
      style={{ flexShrink: 0 }}
    />
  );

  const heading = (
    <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
      <Stack gap={4} style={{ minWidth: 0 }}>
        <Title order={2}>{request.title}</Title>
        <Group gap="xs" c="dimmed">
          <Text fw={600}>{request.year}</Text>
          <Text>•</Text>
          <Text>
            {isMovie
              ? formatRuntime(request.runtime)
              : t('requestCard.season', { season: request.season_number })}
          </Text>
        </Group>
      </Stack>

      <Group gap="sm">
        {languageSelector}
        <StatusBadge status={request.status} size={isMobile ? 'md' : 'lg'} />
      </Group>
    </Group>
  );

  const details = (
    <>
      <SimpleGrid cols={{ base: 2, md: 3 }} spacing="sm">
        <InfoItem label={t('mediaInfo.labels.type')}>
          {isMovie ? `🎬 ${t('mediaType.movie')}` : `📺 ${t('mediaType.series')}`}
        </InfoItem>
        <InfoItem label={t('mediaInfo.labels.created')}>{formatDate(request.created_at)}</InfoItem>
        <InfoItem label={t('mediaInfo.labels.updated')}>{formatDate(request.updated_at)}</InfoItem>
        {!isMovie && (
          <InfoItem label={t('mediaInfo.labels.series')}>
            {request.series_title} ({request.series_year})
          </InfoItem>
        )}
        {!isMovie && (
          <InfoItem label={t('mediaInfo.labels.episodes')}>
            {t('mediaInfo.episodes', { count: request.total_episodes })}
          </InfoItem>
        )}
      </SimpleGrid>

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
   * A phone cannot fit the poster beside the details grid, so only the heading
   * sits next to it and everything else spans the full width underneath.
   */
  if (isMobile) {
    return (
      <Card withBorder radius="lg" padding="md">
        <Stack gap="lg">
          <Group align="flex-start" gap="md" wrap="nowrap">
            {poster}
            <Stack gap="sm" style={{ flex: 1, minWidth: 0 }}>
              {heading}
            </Stack>
          </Group>
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
          {heading}
          {details}
        </Stack>
      </Group>
    </Card>
  );
}
