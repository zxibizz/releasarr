import { Alert, Button, Divider, FileInput, Group, Stack, Text, Textarea } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconFileFilled } from '@tabler/icons-react';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { releasesApi } from '@/features/releases/api';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { ManualReleaseRequest } from '@/types';
import { getErrorMessage } from '@/utils/errors';

const TORRENT_ACCEPT = '.torrent,application/x-bittorrent';

/**
 * `btoa` takes a string, so the bytes go through it in chunks: spreading a
 * whole multi-megabyte torrent into `fromCharCode` at once overflows the
 * argument stack.
 */
const encodeBase64 = (bytes: Uint8Array): string => {
  const CHUNK_SIZE = 0x8000;
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += CHUNK_SIZE) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + CHUNK_SIZE));
  }
  return btoa(binary);
};

const fileToBase64 = async (file: File): Promise<string> =>
  encodeBase64(new Uint8Array(await file.arrayBuffer()));

interface ManualReleaseFormProps {
  requestId: string;
  onDownloadQueued: () => void;
}

export function ManualReleaseForm({ requestId, onDownloadQueued }: ManualReleaseFormProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  const [file, setFile] = useState<File | null>(null);
  const [magnet, setMagnet] = useState('');

  const trimmedMagnet = magnet.replace(/\s+/g, '').trim();
  const magnetLooksWrong = trimmedMagnet.length > 0 && !trimmedMagnet.startsWith('magnet:');

  const reset = () => {
    setFile(null);
    setMagnet('');
  };

  const submit = useMutation({
    mutationFn: async (): Promise<ManualReleaseRequest> => {
      const payload: ManualReleaseRequest = file
        ? { torrent_file_base64: await fileToBase64(file) }
        : { magnet_link: trimmedMagnet };
      await releasesApi.queueManual(requestId, payload);
      return payload;
    },
    onSuccess: () => {
      notifications.show({
        title: t('manualRelease.toasts.queuedTitle'),
        message: t('manualRelease.toasts.queuedDescription'),
        color: 'teal',
      });
      reset();
      onDownloadQueued();
    },
    onError: (error) => {
      notifications.show({
        title: t('manualRelease.toasts.failedTitle'),
        message: getErrorMessage(error, t('manualRelease.toasts.failedFallback')),
        color: 'red',
      });
    },
  });

  // The two inputs are alternatives, not a pair, so filling one empties the
  // other rather than leaving an ambiguous payload to resolve at submit time.
  const handleFileChange = (next: File | null) => {
    setFile(next);
    if (next) {
      setMagnet('');
    }
  };

  const handleMagnetChange = (next: string) => {
    setMagnet(next);
    if (next.trim()) {
      setFile(null);
    }
  };

  const canSubmit = Boolean(file) || (trimmedMagnet.length > 0 && !magnetLooksWrong);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (canSubmit) {
      submit.mutate();
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          {t('manualRelease.instructions')}
        </Text>

        <FileInput
          accept={TORRENT_ACCEPT}
          clearable
          value={file}
          onChange={handleFileChange}
          leftSection={<IconFileFilled size={16} />}
          label={t('manualRelease.file.label')}
          description={t('manualRelease.file.description')}
          placeholder={t('manualRelease.file.placeholder')}
        />

        <Divider label={t('manualRelease.or')} labelPosition="center" />

        <Textarea
          autosize
          minRows={2}
          maxRows={4}
          value={magnet}
          onChange={(event) => handleMagnetChange(event.currentTarget.value)}
          label={t('manualRelease.magnet.label')}
          description={t('manualRelease.magnet.description')}
          placeholder={t('manualRelease.magnet.placeholder')}
          error={magnetLooksWrong ? t('manualRelease.magnet.invalid') : null}
        />

        {submit.isError && (
          <Alert color="red" radius="md">
            {getErrorMessage(submit.error, t('manualRelease.toasts.failedFallback'))}
          </Alert>
        )}

        <Group gap="sm" wrap="nowrap">
          <Button
            type="submit"
            loading={submit.isPending}
            disabled={!canSubmit}
            style={{ flex: isMobile ? 1 : undefined }}
          >
            {t('manualRelease.actions.submit')}
          </Button>
          {(file || magnet) && (
            <Button
              type="button"
              variant="default"
              onClick={reset}
              style={{ flex: isMobile ? 1 : undefined }}
            >
              {t('manualRelease.actions.clear')}
            </Button>
          )}
        </Group>
      </Stack>
    </form>
  );
}
