import { Tabs } from '@mantine/core';
import { IconFolder, IconListCheck } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { ResponsiveModal } from '@/components/ResponsiveModal';
import { FolderPanel } from '@/features/requests/components/FolderPanel';
import { SeasonsPanel } from '@/features/requests/components/SeasonsPanel';
import type { MediaRequest } from '@/types';

interface EditRequestModalProps {
  request: MediaRequest;
  opened: boolean;
  onClose: () => void;
  /** Whether Sonarr or Radarr has linked the request, which a folder move needs. */
  inLibrary: boolean;
  /** Called when the saved seasons no longer cover the season being viewed. */
  onRequestRemoved: () => void;
}

/**
 * Everything about a request that is changed in Sonarr or Radarr, behind the one
 * pencil in its header: the seasons a series is monitored for, and the library
 * folder it is stored in. Tabs only when there is more than one of them to pick
 * from — a movie has no seasons, so it opens straight on its folder.
 */
export function EditRequestModal({
  request,
  opened,
  onClose,
  inLibrary,
  onRequestRemoved,
}: EditRequestModalProps) {
  const { t } = useTranslation();

  const seasons =
    request.type === 'series' ? (
      <SeasonsPanel request={request} onClose={onClose} onRequestRemoved={onRequestRemoved} />
    ) : null;
  const folder = inLibrary ? <FolderPanel request={request} onClose={onClose} /> : null;

  return (
    <ResponsiveModal
      opened={opened}
      onClose={onClose}
      title={t('requestPage.edit.modalTitle', {
        title: request.type === 'series' ? request.series_title : request.title,
      })}
    >
      {seasons && folder ? (
        <Tabs defaultValue="seasons" keepMounted={false}>
          <Tabs.List mb="md">
            <Tabs.Tab value="seasons" leftSection={<IconListCheck size={16} />}>
              {t('requestPage.edit.tabs.seasons')}
            </Tabs.Tab>
            <Tabs.Tab value="folder" leftSection={<IconFolder size={16} />}>
              {t('requestPage.edit.tabs.folder')}
            </Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="seasons">{seasons}</Tabs.Panel>
          <Tabs.Panel value="folder">{folder}</Tabs.Panel>
        </Tabs>
      ) : (
        (seasons ?? folder)
      )}
    </ResponsiveModal>
  );
}
