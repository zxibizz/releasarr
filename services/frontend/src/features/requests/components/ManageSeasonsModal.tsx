import { Alert, Button, Group, Stack, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ResponsiveModal } from '@/components/ResponsiveModal';
import { SeasonPicker } from '@/features/discover/components/SeasonPicker';
import { seasonLabelKey } from '@/features/discover/seasons';
import { useRequestSeasons, useUpdateRequestSeasons } from '@/features/requests/queries';
import { ApiError } from '@/lib/api/client';
import type { SeriesRequest } from '@/types';

interface ManageSeasonsModalProps {
  request: SeriesRequest;
  opened: boolean;
  onClose: () => void;
  /** Called when the saved selection no longer covers the season being viewed. */
  onRequestRemoved: () => void;
}

/**
 * The add-request season picker, pointed at a series already in the library.
 * The ticks here are Sonarr's own monitored flags, read from it and saved
 * straight back: a season monitored in Sonarr shows as ticked whether or not
 * releasarr holds a request for it, which a complete season never does.
 *
 * A season can therefore be untaken, which unmonitors it in Sonarr and deletes
 * whatever request it had — including the request this modal was opened from.
 * Untaking the last one of a series with no file on disk deletes the series from
 * Sonarr too, which the backend reports as the series no longer being in the
 * library.
 */
export function ManageSeasonsModal({
  request,
  opened,
  onClose,
  onRequestRemoved,
}: ManageSeasonsModalProps) {
  const { t } = useTranslation();

  const seasons = useRequestSeasons(request.id, opened);
  const updateSeasons = useUpdateRequestSeasons(request.id);

  const [picked, setPicked] = useState<number[] | null>(null);
  const [pickedNewSeasons, setPickedNewSeasons] = useState<boolean | null>(null);

  const monitoredSeasons = useMemo(
    () =>
      (seasons.data?.seasons ?? [])
        .filter((season) => season.monitored && season.season_number > 0)
        .map((season) => season.season_number),
    [seasons.data],
  );

  // Derived rather than stored, so the selection shows what Sonarr monitors
  // today the moment the seasons arrive, without an effect to copy it across.
  const selected = picked ?? monitoredSeasons;
  const monitorNewSeasons = pickedNewSeasons ?? seasons.data?.monitor_new_seasons ?? false;

  const removing = monitoredSeasons.filter((season) => !selected.includes(season));
  const seasonNames = (numbers: number[]) =>
    numbers.map((season) => t(seasonLabelKey(season), { season })).join(', ');

  const save = () => {
    updateSeasons.mutate(
      { season_numbers: selected, monitor_new_seasons: monitorNewSeasons },
      {
        onSuccess: () => {
          onClose();
          if (request.season_number > 0 && !selected.includes(request.season_number)) {
            onRequestRemoved();
          }
        },
      },
    );
  };

  const handleSave = () => {
    if (removing.length === 0) {
      save();
      return;
    }
    modals.openConfirmModal({
      title: t('requestPage.seasons.removeDialog.title'),
      children: (
        <Text size="sm">
          {t('requestPage.seasons.removeDialog.body', { seasons: seasonNames(removing) })}
        </Text>
      ),
      labels: {
        confirm: t('requestPage.seasons.removeDialog.confirm'),
        cancel: t('common.cancel'),
      },
      confirmProps: { color: 'red' },
      onConfirm: save,
    });
  };

  // Sonarr links a request to a series only once the sync has seen it, and until
  // then there is no season list to offer — which the backend reports as a
  // conflict rather than an outage.
  const unavailable = seasons.error instanceof ApiError && seasons.error.status === 409;

  return (
    <ResponsiveModal
      opened={opened}
      onClose={onClose}
      title={t('requestPage.seasons.modalTitle', { title: request.series_title })}
    >
      <Stack gap="md">
        {unavailable ? (
          <Alert color="yellow" radius="md">
            {t('requestPage.seasons.unavailable')}
          </Alert>
        ) : (
          <SeasonPicker
            seasons={seasons.data?.seasons ?? []}
            selected={selected}
            onChange={setPicked}
            isLoading={seasons.isLoading}
            error={seasons.error}
            allowRemoving
            monitorNewSeasons={monitorNewSeasons}
            onMonitorNewSeasonsChange={setPickedNewSeasons}
          />
        )}

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button
            loading={updateSeasons.isPending}
            disabled={!seasons.isSuccess}
            onClick={handleSave}
          >
            {t('requestPage.seasons.confirm')}
          </Button>
        </Group>
      </Stack>
    </ResponsiveModal>
  );
}
