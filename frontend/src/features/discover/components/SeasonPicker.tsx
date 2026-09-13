import {
  Alert,
  Anchor,
  Checkbox,
  Divider,
  Group,
  Skeleton,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core';
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
  /**
   * Lets a season that already has a request be unticked, which is what turns
   * the picker into a manager: the selection then describes what the series
   * should hold requests for rather than what to add to it.
   */
  allowRemoving?: boolean;
  monitorNewSeasons?: boolean;
  onMonitorNewSeasonsChange?: (monitor: boolean) => void;
}

/**
 * Seasons that already have a request show as ticked. Where they cannot be
 * removed they are locked too: requesting one again is harmless — the backend
 * refreshes the existing row — but offering it as a choice invites the user to
 * look for a difference that isn't there.
 *
 * Specials are left out entirely: they are rarely what someone means by "the
 * next season", and TVDB files anything without a home there.
 */
export function SeasonPicker({
  seasons,
  selected,
  onChange,
  isLoading,
  error,
  allowRemoving = false,
  monitorNewSeasons,
  onMonitorNewSeasonsChange,
}: SeasonPickerProps) {
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

  const isLocked = (season: SeasonOption) => season.requested && !allowRemoving;
  const selectable = offered.filter((season) => !isLocked(season));
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
            checked={isLocked(season) || selected.includes(season.season_number)}
            disabled={isLocked(season)}
            label={t(seasonLabelKey(season.season_number), { season: season.season_number })}
            description={isLocked(season) ? t('discover.seasons.alreadyRequested') : undefined}
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

      {/*
        Future seasons are a property of the series rather than one of the
        numbered seasons, so they sit below the grid instead of in it.
      */}
      {onMonitorNewSeasonsChange && (
        <>
          <Divider my={4} />
          <Checkbox
            checked={monitorNewSeasons ?? false}
            label={t('discover.seasons.newSeasons')}
            description={t('discover.seasons.newSeasonsHint')}
            onChange={(event) => onMonitorNewSeasonsChange(event.currentTarget.checked)}
          />
        </>
      )}
    </Stack>
  );
}
