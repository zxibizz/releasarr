import { Alert, Button, Group, Select, Stack, Text } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ResponsiveModal } from '@/components/ResponsiveModal';
import { SeasonPicker } from '@/features/discover/components/SeasonPicker';
import { useAddRequest, useRootFolders, useSeriesSeasons } from '@/features/discover/queries';
import type { MediaSearchResult } from '@/types';
import { formatFileSize } from '@/utils/formatters';

interface AddRequestModalProps {
  media: MediaSearchResult | null;
  onClose: () => void;
}

export function AddRequestModal({ media, onClose }: AddRequestModalProps) {
  if (!media) {
    return null;
  }

  const title = media.year ? `${media.title} (${media.year})` : media.title;

  return (
    <ResponsiveModal opened onClose={onClose} title={title}>
      {/*
        Keyed on the picked result so switching results discards the folder and
        season choices with the form that holds them, rather than carrying them
        over to a title they were never made for.
      */}
      <AddRequestForm key={`${media.type}-${media.provider_id}`} media={media} onClose={onClose} />
    </ResponsiveModal>
  );
}

function AddRequestForm({ media, onClose }: { media: MediaSearchResult; onClose: () => void }) {
  const { t } = useTranslation();
  const isSeries = media.type === 'series';

  const [pickedFolder, setPickedFolder] = useState<string | null>(null);
  const [seasons, setSeasons] = useState<number[]>([]);

  const rootFolders = useRootFolders(media.type);
  const seasonOptions = useSeriesSeasons(isSeries ? media.provider_id : undefined);
  const addRequest = useAddRequest();

  const folders = rootFolders.data?.folders ?? [];
  // Most installs have a single library location, and asking the user to confirm
  // the only answer is noise. Derived rather than stored so the default appears
  // as soon as the folders arrive.
  const rootFolder = pickedFolder ?? folders[0]?.path ?? null;

  /*
   * Sonarr and Radarr own the path of media they already hold, and the backend
   * ignores the one we send for it, so asking would imply a move that will not
   * happen. Series fall back to the search result until the exact lookup lands.
   */
  const inLibrary = isSeries
    ? (seasonOptions.data?.in_library ?? media.in_library)
    : media.in_library;
  const canSubmit = (isSeries ? seasons.length > 0 : true) && (inLibrary || Boolean(rootFolder));

  const handleSubmit = () => {
    addRequest.mutate(
      {
        type: media.type,
        provider_id: media.provider_id,
        root_folder_path: rootFolder ?? '',
        season_numbers: isSeries ? seasons : undefined,
      },
      { onSuccess: onClose },
    );
  };

  return (
    <Stack gap="md">
      {inLibrary && (
        <Alert color="blue" radius="md">
          {t(isSeries ? 'discover.modal.inLibrarySeries' : 'discover.modal.inLibraryMovie')}
        </Alert>
      )}

      {!inLibrary && (
        <Select
          label={t('discover.modal.rootFolder')}
          description={t('discover.modal.rootFolderHint')}
          placeholder={t('discover.modal.rootFolderPlaceholder')}
          allowDeselect={false}
          value={rootFolder}
          onChange={setPickedFolder}
          disabled={rootFolders.isLoading}
          error={rootFolders.isError ? t('discover.modal.rootFolderFailed') : undefined}
          data={folders.map((folder) => ({
            value: folder.path,
            label:
              folder.free_space === null || folder.free_space === undefined
                ? folder.path
                : t('discover.modal.rootFolderOption', {
                    path: folder.path,
                    free: formatFileSize(folder.free_space),
                  }),
          }))}
        />
      )}

      {isSeries && (
        <SeasonPicker
          seasons={seasonOptions.data?.seasons ?? []}
          selected={seasons}
          onChange={setSeasons}
          isLoading={seasonOptions.isLoading}
          error={seasonOptions.error}
        />
      )}

      {!inLibrary && !rootFolders.isLoading && folders.length === 0 && (
        <Text size="sm" c="dimmed">
          {t('discover.modal.noRootFolders')}
        </Text>
      )}

      <Group justify="flex-end" gap="sm">
        <Button variant="default" onClick={onClose}>
          {t('common.cancel')}
        </Button>
        <Button loading={addRequest.isPending} disabled={!canSubmit} onClick={handleSubmit}>
          {t('discover.modal.confirm')}
        </Button>
      </Group>
    </Stack>
  );
}
