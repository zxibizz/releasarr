import { Badge, Button, Card, Group, Image, Stack, Text, Title } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { StatusBadge } from '@/components/StatusBadge';
import { seasonLabelKey } from '@/features/discover/seasons';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { MediaSearchResult } from '@/types';

interface MediaSearchResultCardProps {
  result: MediaSearchResult;
  onPick: (result: MediaSearchResult) => void;
}

/**
 * A search hit, with whatever releasarr already knows about it. The library and
 * request badges are the point of the card: without them the same title looks
 * equally addable whether it is missing, monitored or already downloading.
 */
export function MediaSearchResultCard({ result, onPick }: MediaSearchResultCardProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const isSeries = result.type === 'series';
  const requestedSeasons = result.requested_seasons ?? [];

  return (
    <Card withBorder radius="lg" padding={isMobile ? 'sm' : 'lg'} style={{ height: '100%' }}>
      <Group align="flex-start" wrap="nowrap" gap="md" h="100%">
        <Image
          src={result.poster_url ?? undefined}
          alt={t('requestCard.posterAlt', { title: result.title })}
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
              {result.title}
            </Title>
            {result.year && (
              <Text size="sm" c="dimmed">
                {result.year}
              </Text>
            )}
          </div>

          <Group gap="xs">
            {/*
              A search can span both kinds at once, so a result has to say which
              it is; the badge matches the one the request list uses.
            */}
            <Badge color={isSeries ? 'blue' : 'red'} variant="light" radius="sm">
              {isSeries ? '📺' : '🎬'} {t(`mediaType.${result.type}`)}
            </Badge>

            {result.in_library && (
              <Badge color="teal" variant="light" radius="sm">
                {t('discover.badges.inLibrary')}
              </Badge>
            )}

            {/*
              A movie has at most one request, so its status says everything. A
              series has one per season, and which seasons is the useful part.
            */}
            {!isSeries && result.request_status && <StatusBadge status={result.request_status} />}
            {isSeries && requestedSeasons.length > 0 && (
              <Badge color="grape" variant="light" radius="sm">
                {t('discover.badges.requestedSeasons', {
                  seasons: requestedSeasons
                    .map((season) => t(seasonLabelKey(season), { season }))
                    .join(', '),
                })}
              </Badge>
            )}
          </Group>

          {!isMobile && result.overview && (
            <Text size="sm" c="gray.4" lineClamp={3}>
              {result.overview}
            </Text>
          )}

          <Group gap="xs" mt="auto">
            <Button
              size="xs"
              variant={result.in_library ? 'light' : 'filled'}
              onClick={() => onPick(result)}
            >
              {t(isSeries ? 'discover.actions.pickSeasons' : 'discover.actions.request')}
            </Button>
            {/* A movie already requested has a page of its own worth reaching. */}
            {result.request_id && (
              <Button
                size="xs"
                variant="subtle"
                component={Link}
                to={`/request/${result.request_id}`}
              >
                {t('discover.actions.viewRequest')}
              </Button>
            )}
          </Group>
        </Stack>
      </Group>
    </Card>
  );
}
