import type { Release } from '@/types';

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
