import { Tabs } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ResponsiveModal } from '@/components/ResponsiveModal';
import { ReleaseContentTab } from '@/features/releases/components/ReleaseContentTab';
import { ReleaseGeneralTab } from '@/features/releases/components/ReleaseGeneralTab';
import { FileMappingForm } from '@/features/releases/fileMapping/FileMappingForm';
import type { MediaRequest, Release } from '@/types';

type DetailsTab = 'general' | 'content';

const FIRST_TAB: DetailsTab = 'general';

interface ReleaseDetailsModalProps {
  release: Release | null;
  currentRequest: MediaRequest;
  opened: boolean;
  onClose: () => void;
}

/**
 * One release, in two parts: what is known about it, and what it holds. The
 * mapping editor is a mode of the content list rather than a tab of its own, so
 * the files are read-only until the reader asks to change them.
 */
export function ReleaseDetailsModal({
  release,
  currentRequest,
  opened,
  onClose,
}: ReleaseDetailsModalProps) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<DetailsTab>(FIRST_TAB);
  const [isEditingMapping, setEditingMapping] = useState(false);

  /*
   * A mode belongs to one visit: closing the window, or opening it for another
   * release, starts again on General with the list read-only. Synced during the
   * render rather than from an effect, which would paint the old tab once more
   * before correcting it.
   */
  const [seenVisit, setSeenVisit] = useState({ opened, releaseId: release?.id });
  if (seenVisit.opened !== opened || seenVisit.releaseId !== release?.id) {
    setSeenVisit({ opened, releaseId: release?.id });
    setTab(FIRST_TAB);
    setEditingMapping(false);
  }

  if (!release) {
    return null;
  }

  const changeTab = (next: string | null) => setTab(next === 'content' ? 'content' : FIRST_TAB);

  return (
    <ResponsiveModal opened={opened} onClose={onClose} title={`📁 ${release.name}`}>
      <Tabs value={tab} onChange={changeTab}>
        <Tabs.List grow>
          <Tabs.Tab value="general">{t('releaseDetails.tabs.general')}</Tabs.Tab>
          <Tabs.Tab value="content">{t('releaseDetails.tabs.content')}</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="general" pt="md">
          <ReleaseGeneralTab release={release} currentRequestId={currentRequest.id} />
        </Tabs.Panel>

        <Tabs.Panel value="content" pt="md">
          {isEditingMapping ? (
            <FileMappingForm
              releaseId={release.id}
              requestId={currentRequest.id}
              files={release.files}
              showHeading={false}
              onSaved={() => setEditingMapping(false)}
              onCancel={() => setEditingMapping(false)}
            />
          ) : (
            <ReleaseContentTab release={release} onEditMapping={() => setEditingMapping(true)} />
          )}
        </Tabs.Panel>
      </Tabs>
    </ResponsiveModal>
  );
}
