import { useMemo } from 'react';

import { useRequestsList } from '@/features/requests/queries';
import type { Release } from '@/types';

/** The other requests this release is linked to, without the one being viewed. */
export const relatedRequestIds = (release: Release, currentRequestId: string): string[] =>
  [...new Set(release.request_ids ?? [])].filter((id) => id !== currentRequestId);

/**
 * Titles for those ids. The requests list is already cached by the home route
 * loader, so naming a release's siblings costs no extra call.
 */
export function useRelatedRequestTitles(): Map<string, string> {
  const { requests } = useRequestsList();

  return useMemo(() => new Map(requests.map((request) => [request.id, request.title])), [requests]);
}
