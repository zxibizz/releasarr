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
   * the picker into a manager: the selection then describes what Sonarr should
   * monitor rather than what to add to the series.
   */
  allowRemoving?: boolean;
  monitorNewSeasons?: boolean;
  onMonitorNewSeasonsChange?: (monitor: boolean) => void;
}

/**
 * What a tick means depends on the caller. Adding a request, it is a season to
 * ask for, and a season Sonarr already covers — requested by us, or monitored
 * by it — is ticked and locked: asking again is harmless, but offering it as a
 * choice both invites the user to look for a difference that isn't there and
 * misreports what Sonarr is doing. Managing a series (`allowRemoving`), a tick
 * is Sonarr's monitored flag, which the caller both seeds from and saves to.
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

  /*
   * Adding, a season is out of the running once Sonarr already covers it, by a
   * request of ours or by its own monitoring. An add only ever widens
   * monitoring, so there is nothing left to ask for and no way to give it back
   * from here - that is the manage-seasons modal's job.
   */
  const isCovered = (season: SeasonOption) =>
    (season.requested || season.monitored) && !allowRemoving;
  const selectable = offered.filter((season) => !isCovered(season));
  const selectableNumbers = selectable.map((season) => season.season_number);
  const allSelected =
    selectable.length > 0 && selectableNumbers.every((number) => selected.includes(number));
  const rows = Math.ceil(offered.length / columns);

  const coveredNote = (season: SeasonOption) =>
    season.requested
      ? t('discover.seasons.alreadyRequested')
      : t('discover.seasons.alreadyMonitored');

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
            // A season already covered reads as chosen, because it is.
            checked={isCovered(season) || selected.includes(season.season_number)}
            disabled={isCovered(season)}
            label={t(seasonLabelKey(season.season_number), { season: season.season_number })}
            description={isCovered(season) ? coveredNote(season) : undefined}
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
        Every box ticked and none of them yours to change leaves the submit
        button disabled, so say why rather than let it read as broken.
      */}
      {selectable.length === 0 && (
        <Text size="sm" c="dimmed">
          {t('discover.seasons.allCovered')}
        </Text>
      )}

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
