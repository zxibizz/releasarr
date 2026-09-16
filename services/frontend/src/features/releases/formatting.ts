import type { TFunction } from 'i18next';

import type { Release } from '@/types';
import { daysSince } from '@/utils/formatters';

/**
 * How well seeded a release is, as a percentage of its peers. A release nobody
 * is competing for is the healthy case, so no leechers reads as 100 rather than
 * as a divide by zero.
 */
export const releaseHealthScore = (release: Release): number => {
  if (release.seeders === 0) return 0;
  if (release.leechers === 0) return 100;
  return Math.round((release.seeders / (release.seeders + release.leechers)) * 100);
};

export const healthColor = (score: number): string => {
  if (score >= 70) return 'teal';
  if (score >= 40) return 'yellow';
  return 'red';
};

/** The release's age in the words the search results already use for one. */
export const releaseAgeLabel = (release: Release, t: TFunction): string => {
  const days = daysSince(release.published_date);
  if (days === null) return t('releaseSearch.age.unknown');
  if (days < 1) return t('releaseSearch.age.today');
  return t('releaseSearch.age.days', { count: Math.floor(days) });
};
