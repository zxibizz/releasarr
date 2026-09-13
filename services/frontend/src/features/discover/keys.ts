import type { MediaType } from '@/types';

/**
 * Kept apart from the hooks because both features invalidate each other: adding
 * or withdrawing a request changes what the search results report about it, and
 * the request list changes with it. Importing the keys alone keeps that from
 * becoming a cycle between the two query modules.
 */
export const discoverKeys = {
  all: ['discover'] as const,
  search: (query: string, language: string) =>
    [...discoverKeys.all, 'search', language, query] as const,
  seasons: (tvdbId: number) => [...discoverKeys.all, 'seasons', tvdbId] as const,
  rootFolders: (type: MediaType) => [...discoverKeys.all, 'root-folders', type] as const,
};
