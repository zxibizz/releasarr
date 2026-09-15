import type { Release, ReleaseWarning } from '@/types';

/** Whether any file in this release is part of a mapping overlap. */
export const hasMappingOverlap = (release: Release): boolean =>
  (release.warnings ?? []).some((warning) => warning.code === 'mapping_overlap');

/** File ids on this release flagged as overlapping - with themselves or another release. */
export const overlappingFileIds = (release: Release): Set<string> => {
  const ids = new Set<string>();
  (release.warnings ?? []).forEach((warning) => {
    warning.file_ids.forEach((id) => ids.add(id));
  });
  return ids;
};

/** How many other releases this one's mapping overlaps with, across all warnings. */
export const overlapRelatedReleaseCount = (release: Release): number => {
  const ids = new Set<string>();
  (release.warnings ?? []).forEach((warning) => {
    warning.related_release_ids.forEach((id) => ids.add(id));
  });
  return ids.size;
};

/** Why the last regrab check couldn't reach this release's indexer, if it failed. */
export const regrabUnavailableReason = (release: Release): string | null => {
  const warning = (release.warnings ?? []).find(
    (candidate) => candidate.code === 'regrab_indexer_unavailable',
  );
  const reason = warning?.details?.reason;
  return typeof reason === 'string' ? reason : null;
};

/** The indexer that no longer lists this release, if a check found it missing there. */
export const notListedIndexer = (release: Release): string | null => {
  const warning = (release.warnings ?? []).find(
    (candidate) => candidate.code === 'release_not_listed',
  );
  const indexer = warning?.details?.indexer;
  return typeof indexer === 'string' ? indexer : null;
};

/** The file count a re-grab warning carries, or null when the release has no such warning. */
const regrabFileCount = (release: Release, code: ReleaseWarning['code']): number | null => {
  const count = (release.warnings ?? []).find((warning) => warning.code === code)?.details
    ?.file_count;
  return typeof count === 'number' ? count : null;
};

/** How many files a replacement torrent added that automapping could not place. */
export const unmappedRegrabFileCount = (release: Release): number | null =>
  regrabFileCount(release, 'regrab_files_unmapped');

/** How many files a refused replacement torrent was missing, if a re-grab was refused. */
export const missingRegrabFileCount = (release: Release): number | null =>
  regrabFileCount(release, 'regrab_files_missing');
