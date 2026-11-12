import { Alert, Button, Group, Select, Stack, Text } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ResponsiveModal } from '@/components/ResponsiveModal';
import { useRootFolders } from '@/features/discover/queries';
import { useMoveLibraryFolder, useRequestLibraryFolder } from '@/features/requests/queries';
import { ApiError } from '@/lib/api/client';
import type { MediaRequest } from '@/types';
import { formatFileSize } from '@/utils/formatters';

interface MoveFolderModalProps {
  request: MediaRequest;
  opened: boolean;
  onClose: () => void;
}

/**
 * Moves the series or movie behind a request to another library folder. The
 * folder is what a media server library is pointed at, so this is how a title
 * added to the wrong one — and shown to the wrong people — is put right.
 *
 * Sonarr keeps one folder per series, so the whole series moves, every season's
 * request with it; the modal says so rather than let the season in the title
 * suggest otherwise.
 */
export function MoveFolderModal({ request, opened, onClose }: MoveFolderModalProps) {
  const { t } = useTranslation();
  const isSeries = request.type === 'series';

  const current = useRequestLibraryFolder(request.id, opened);
  const rootFolders = useRootFolders(request.type, { enabled: opened });
  const move = useMoveLibraryFolder(request.id);

  const [picked, setPicked] = useState<string | null>(null);

  const currentFolder = current.data?.root_folder_path ?? null;
  const folders = rootFolders.data?.folders ?? [];
  // Derived rather than stored, so the picker opens on the folder the title is
  // in the moment the answer arrives.
  const selected = picked ?? currentFolder;

  const unavailable = current.error instanceof ApiError && current.error.status === 409;
  const canMove = Boolean(selected) && selected !== currentFolder && current.isSuccess;

  const handleClose = () => {
    setPicked(null);
    onClose();
  };

  const handleMove = () => {
    if (!selected) return;
    move.mutate(selected, { onSuccess: handleClose });
  };

  return (
    <ResponsiveModal
      opened={opened}
      onClose={handleClose}
      title={t('requestPage.folder.modalTitle', {
        title: isSeries ? request.series_title : request.title,
      })}
    >
      <Stack gap="md">
        {unavailable ? (
          <Alert color="yellow" radius="md">
            {t(
              isSeries
                ? 'requestPage.folder.unavailableSeries'
                : 'requestPage.folder.unavailableMovie',
            )}
          </Alert>
        ) : (
          <>
            {current.data?.path && (
              <Text size="sm" c="dimmed" className="break-anywhere">
                {t('requestPage.folder.currentPath', { path: current.data.path })}
              </Text>
            )}
            <Select
              label={t('requestPage.folder.label')}
              placeholder={t('discover.modal.rootFolderPlaceholder')}
              allowDeselect={false}
              value={selected}
              onChange={setPicked}
              disabled={current.isLoading || rootFolders.isLoading}
              error={
                current.isError || rootFolders.isError
                  ? t('requestPage.folder.loadFailed')
                  : undefined
              }
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
            <Alert color="blue" radius="md">
              {t(isSeries ? 'requestPage.folder.hintSeries' : 'requestPage.folder.hintMovie')}
            </Alert>
          </>
        )}

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleClose}>
            {t('common.cancel')}
          </Button>
          <Button loading={move.isPending} disabled={!canMove} onClick={handleMove}>
            {t('requestPage.folder.confirm')}
          </Button>
        </Group>
      </Stack>
    </ResponsiveModal>
  );
}
