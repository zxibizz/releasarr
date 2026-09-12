import { Alert, Anchor, Checkbox, Group, Skeleton, SimpleGrid, Stack, Text } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { seasonLabelKey } from '@/features/discover/seasons';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { SeasonOption } from '@/types';
import { getErrorMessage } from '@/utils/errors';

interface SeasonPickerProps {
  seasons: SeasonOption[];
  selected: number[];
  onChange: (seasons: number[]) => void;
  isLoading: boolean;
  error: unknown;
}

/**
 * Seasons that already have a request show as ticked but locked. Requesting one
 * again is harmless — the backend refreshes the existing row — but offering it as
 * a choice invites the user to look for a difference that isn't there.
 *
 * Specials are left out entirely: they are rarely what someone means by "the
 * next season", and TVDB files anything without a home there.
 */
export function SeasonPicker({ seasons, selected, onChange, isLoading, error }: SeasonPickerProps) {
  const { t } = useTranslation();
  // The same breakpoint the grid's own columns switch at, so the column count
  // driving the layout below and the one the CSS uses cannot disagree.
  const columns = useIsMobile() ? 2 : 3;

  if (isLoading) {
    return (
      <Stack gap="xs">
        <Skeleton height={12} width={120} />
        <Skeleton height={80} />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert color="red" radius="md">
        {getErrorMessage(error, t('discover.seasons.loadFailed'))}
      </Alert>
    );
  }

  const offered = seasons.filter((season) => season.season_number > 0);

  if (offered.length === 0) {
    return (
      <Alert color="yellow" radius="md">
        {t('discover.seasons.none')}
      </Alert>
    );
  }

  const selectable = offered.filter((season) => !season.requested);
  const selectableNumbers = selectable.map((season) => season.season_number);
  const allSelected =
    selectable.length > 0 && selectableNumbers.every((number) => selected.includes(number));
  const rows = Math.ceil(offered.length / columns);

  return (
    <Stack gap="xs">
      <Group justify="space-between" align="baseline" wrap="nowrap">
        <Text size="sm" fw={600}>
          {t('discover.seasons.label')}
        </Text>
        {selectable.length > 1 && (
          <Anchor
            component="button"
            type="button"
            size="sm"
            onClick={() => onChange(allSelected ? [] : selectableNumbers)}
          >
            {t(allSelected ? 'discover.seasons.clearAll' : 'discover.seasons.selectAll')}
          </Anchor>
        )}
      </Group>

      {/*
        Seasons read down each column rather than across each row, which is the
        order they are numbered in. Laid out by CSS rather than by reordering the
        list, so the tab order still follows the seasons as they appear.
      */}
      <SimpleGrid
        cols={columns}
        spacing="xs"
        verticalSpacing="xs"
        style={{ gridAutoFlow: 'column', gridTemplateRows: `repeat(${rows}, auto)` }}
      >
        {offered.map((season) => (
          <Checkbox
            key={season.season_number}
            // A season already requested reads as chosen, because it is.
            checked={season.requested || selected.includes(season.season_number)}
            disabled={season.requested}
            label={t(seasonLabelKey(season.season_number), { season: season.season_number })}
            description={season.requested ? t('discover.seasons.alreadyRequested') : undefined}
            onChange={(event) =>
              onChange(
                event.currentTarget.checked
                  ? [...selected, season.season_number]
                  : selected.filter((number) => number !== season.season_number),
              )
            }
          />
        ))}
      </SimpleGrid>
    </Stack>
  );
}
