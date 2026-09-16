import { Alert, Button, Group, Stack, Text, Title } from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { OtherFilesSection } from '@/features/releases/components/OtherFilesSection';
import { FileMappingRow } from '@/features/releases/fileMapping/FileMappingRow';
import { FileMappingToolbar } from '@/features/releases/fileMapping/FileMappingToolbar';
import { useFileMappingForm } from '@/features/releases/fileMapping/useFileMappingForm';
import { useSuggestedFileMappings, useUpdateFileMappings } from '@/features/releases/queries';
import { useRequestsList } from '@/features/requests/queries';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { ReleaseFile } from '@/types';
import { getErrorMessage } from '@/utils/errors';
import { commonRootFolder, splitVideoFiles } from '@/utils/files';

interface FileMappingFormProps {
  releaseId: string;
  requestId: string;
  files: ReleaseFile[];
  /** Off when the form is the body of a tab that already says what it is. */
  showHeading?: boolean;
  /** Called once the mappings are stored, for a caller that opened the form as a mode. */
  onSaved?: () => void;
  /** Adds a way out of the form that does not save; confirm-then-discard when dirty. */
  onCancel?: () => void;
}

export function FileMappingForm({
  releaseId,
  requestId,
  files,
  showHeading = true,
  onSaved,
  onCancel,
}: FileMappingFormProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  // Stretched to share a row on a phone; left at their natural width otherwise,
  // since growing them lets flexbox shrink the labels below their text.
  const buttonFlex = isMobile ? '1 1 140px' : undefined;

  const { requests, isLoading: requestsLoading } = useRequestsList();
  const availableRequests = useMemo(
    () => requests.filter((request) => request.status !== 'failed'),
    [requests],
  );

  // The proposals arrive after the first paint, so the rows start out as
  // whatever is stored and fill in from there.
  const { data: suggestions, isPending: suggestionsPending } = useSuggestedFileMappings(releaseId);

  const form = useFileMappingForm(files, availableRequests, suggestions);
  const saveMappings = useUpdateFileMappings(releaseId, requestId);

  const { video, other } = useMemo(() => splitVideoFiles(files), [files]);
  const orderedFiles = useMemo(() => [...video, ...other], [video, other]);
  const rootFolder = useMemo(() => commonRootFolder(files), [files]);

  // A release belongs to a request before anybody opens it, so automapping maps
  // to this one rather than asking. A failed request is not a mapping target.
  const targetRequest = availableRequests.find((request) => request.id === requestId);

  const hasChanges = form.dirtyFileIds.length > 0;

  const handleSave = async () => {
    const payload = form.buildPayload(orderedFiles);

    if (payload.length === 0) {
      notifications.show({
        title: t('fileMapping.nothingToSave', { defaultValue: 'Nothing to save' }),
        message: t('fileMapping.nothingToSaveHint', {
          defaultValue: 'Select at least one request before saving.',
        }),
        color: 'blue',
      });
      return;
    }

    try {
      await saveMappings.mutateAsync(payload);
      notifications.show({
        title: t('fileMapping.saved', { defaultValue: 'Mappings saved' }),
        message: t('fileMapping.savedCount', {
          defaultValue: '{{count}} file mapping(s) updated.',
          count: payload.length,
        }),
        color: 'teal',
      });
      onSaved?.();
    } catch (error) {
      notifications.show({
        title: t('fileMapping.saveFailed', { defaultValue: 'Failed to save mappings' }),
        message: getErrorMessage(error, ''),
        color: 'red',
      });
    }
  };

  const leaveWithoutSaving = () => {
    if (!hasChanges) {
      onCancel?.();
      return;
    }

    modals.openConfirmModal({
      title: t('releaseDetails.editMode.discard.title'),
      children: <Text size="sm">{t('releaseDetails.editMode.discard.body')}</Text>,
      labels: {
        confirm: t('releaseDetails.editMode.discard.confirm'),
        cancel: t('common.cancel'),
      },
      confirmProps: { color: 'red' },
      onConfirm: () => onCancel?.(),
    });
  };

  const renderRow = (file: ReleaseFile) => (
    <FileMappingRow
      key={file.id}
      file={file}
      rootFolder={rootFolder}
      draft={form.getDraft(file.id)}
      requests={availableRequests}
      requestsDisabled={requestsLoading || availableRequests.length === 0}
      isDirty={form.isDirty(file.id)}
      onSelectRequest={(request) => form.selectRequest(file.id, request)}
      onChange={(changes) => form.updateDraft(file.id, changes)}
    />
  );

  return (
    <Stack gap="lg">
      {showHeading && (
        <Stack gap={4}>
          <Title order={4}>
            🔗 {t('fileMapping.title', { defaultValue: 'File request mapping' })}
          </Title>
          <Text size="sm" c="dimmed">
            {t('fileMapping.description', {
              defaultValue: 'Map release files to requests to manage shared content.',
            })}
          </Text>
        </Stack>
      )}

      {/*
       * Numbering stays on the videos: a sample or an NFO is never the next
       * episode, and the odd subtitle that is wanted is a single row away.
       */}
      <FileMappingToolbar
        /*
         * Automapping before the proposals are here would blank every stored
         * mapping only for the arriving proposals to leave those rows alone:
         * the sync fills in untouched rows, and these are no longer untouched.
         */
        canAutomap={!suggestionsPending && Boolean(targetRequest)}
        onAutomap={() => form.automap(targetRequest, video)}
      />

      {availableRequests.length === 0 && !requestsLoading && (
        <Alert color="blue" radius="md">
          {t('fileMapping.noRequests', {
            defaultValue: 'No requests are available to map files to yet.',
          })}
        </Alert>
      )}

      {files.length === 0 ? (
        <EmptyState
          icon="📁"
          title={t('fileMapping.empty.title', { defaultValue: 'No files to map' })}
          description={t('fileMapping.empty.description', {
            defaultValue: 'No files are available for mapping.',
          })}
        />
      ) : (
        <Stack gap="sm">
          {video.map(renderRow)}
          <OtherFilesSection count={other.length}>{other.map(renderRow)}</OtherFilesSection>
        </Stack>
      )}

      <Group justify="flex-end" gap="sm" wrap="wrap">
        <Text size="sm" c="dimmed" mr={{ base: 0, sm: 'auto' }}>
          {hasChanges
            ? t('fileMapping.pendingChanges', {
                defaultValue: '{{count}} unsaved change(s)',
                count: form.dirtyFileIds.length,
              })
            : t('fileMapping.noChanges', { defaultValue: 'No unsaved changes' })}
        </Text>
        <Group gap="sm" wrap="wrap" w={{ base: '100%', sm: 'auto' }}>
          {onCancel && (
            <Button variant="default" onClick={leaveWithoutSaving} style={{ flex: buttonFlex }}>
              {t('common.cancel')}
            </Button>
          )}
          <Button
            variant="default"
            onClick={form.reset}
            disabled={!hasChanges}
            style={{ flex: buttonFlex }}
          >
            {t('fileMapping.undoAll', { defaultValue: 'Undo all changes' })}
          </Button>
          <Button
            onClick={handleSave}
            loading={saveMappings.isPending}
            style={{ flex: buttonFlex }}
          >
            {t('fileMapping.saveAll', { defaultValue: 'Save mappings' })}
          </Button>
        </Group>
      </Group>
    </Stack>
  );
}
