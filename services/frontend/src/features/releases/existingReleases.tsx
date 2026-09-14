import { Button, Group, Stack, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import type { TFunction } from 'i18next';

import { ApiError } from '@/lib/api/client';
import type { ExistingReleasesAction, Release } from '@/types';

const DECISION_REQUIRED_CODE = 'existing_releases_decision_required';

/** Whether a grab was rejected because the request already has releases. */
export const isExistingReleasesDecisionRequired = (error: unknown): boolean =>
  error instanceof ApiError &&
  error.status === 409 &&
  typeof error.details === 'object' &&
  error.details !== null &&
  (error.details as { code?: unknown }).code === DECISION_REQUIRED_CODE;

/** The release ids the server reported as already existing, from a 409 body. */
export const existingReleaseIdsFromError = (error: unknown): string[] => {
  if (!(error instanceof ApiError) || typeof error.details !== 'object' || error.details === null) {
    return [];
  }
  const details = (error.details as { details?: { release_ids?: unknown } }).details;
  const ids = details?.release_ids;
  return Array.isArray(ids) ? ids.filter((id): id is string => typeof id === 'string') : [];
};

/**
 * Ask what to do with a request's other releases before grabbing a new one.
 * Resolves to the decision, or null if the user dismissed the dialog - the
 * caller must not queue the grab in that case.
 */
export function confirmExistingReleases(
  existingReleases: Release[],
  t: TFunction,
): Promise<ExistingReleasesAction | null> {
  return new Promise((resolve) => {
    const modalId = 'existing-releases-decision';
    let decided = false;

    const finish = (decision: ExistingReleasesAction | null) => {
      decided = true;
      modals.close(modalId);
      resolve(decision);
    };

    modals.open({
      modalId,
      title: t('existingReleases.title', {
        defaultValue: 'This request already has releases',
      }),
      centered: true,
      onClose: () => {
        if (!decided) resolve(null);
      },
      children: (
        <Stack gap="md">
          <Text size="sm">
            {t('existingReleases.body', {
              defaultValue:
                'Keep the {{count}} existing release(s) alongside the new one, or delete the ones grabbed only for this request.',
              count: existingReleases.length,
            })}
          </Text>
          <Stack gap={4}>
            {existingReleases.map((release) => (
              <Text key={release.id} size="sm" c="dimmed" lineClamp={1}>
                {release.name}
              </Text>
            ))}
          </Stack>
          <Group justify="flex-end" gap="sm">
            <Button variant="default" onClick={() => finish(null)}>
              {t('common.cancel')}
            </Button>
            <Button variant="light" onClick={() => finish('keep')}>
              {t('existingReleases.keep', { defaultValue: 'Keep both' })}
            </Button>
            <Button color="red" onClick={() => finish('replace')}>
              {t('existingReleases.replace', { defaultValue: 'Delete existing' })}
            </Button>
          </Group>
        </Stack>
      ),
    });
  });
}
