import { requestStatusStyles, releaseStatusStyles } from '@/theme/statusStyles';
import type { MediaRequest, MediaRequestStatus, Release, ReleaseStatus } from '@/types';

interface StatusBadgeStyle {
  bg: string;
  color: string;
  borderColor: string;
}

export interface StatusPresentation {
  value: string;
  label: string;
  icon: string;
  badge: StatusBadgeStyle;
}

const toSentenceCase = (value: string): string => {
  if (!value) {
    return '';
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
};

const buildPresentation = (
  value: string,
  icon: string,
  badge: StatusBadgeStyle,
  label?: string,
): StatusPresentation => ({
  value,
  label: label ?? toSentenceCase(value),
  icon,
  badge,
});

const REQUEST_STATUS_PRESENTATIONS: Record<MediaRequestStatus, StatusPresentation> = {
  pending: buildPresentation('pending', '⏳', requestStatusStyles.pending, 'Pending'),
  searching: buildPresentation('searching', '🔍', requestStatusStyles.searching, 'Searching'),
  downloading: buildPresentation('downloading', '⬇️', requestStatusStyles.downloading, 'Downloading'),
  completed: buildPresentation('completed', '✅', requestStatusStyles.completed, 'Completed'),
  failed: buildPresentation('failed', '❌', requestStatusStyles.failed, 'Failed'),
};

const RELEASE_STATUS_PRESENTATIONS: Record<ReleaseStatus, StatusPresentation> = {
  pending: buildPresentation('pending', '⏳', releaseStatusStyles.pending, 'Pending'),
  downloading: buildPresentation('downloading', '⬇️', releaseStatusStyles.downloading, 'Downloading'),
  seeding: buildPresentation('seeding', '🌱', releaseStatusStyles.seeding, 'Seeding'),
  completed: buildPresentation('completed', '✅', releaseStatusStyles.completed, 'Completed'),
  failed: buildPresentation('failed', '❌', releaseStatusStyles.failed, 'Failed'),
};

const fallbackRequestPresentation = buildPresentation(
  'unknown',
  '❓',
  requestStatusStyles.pending,
  'Unknown',
);

const fallbackReleasePresentation = buildPresentation(
  'unknown',
  '❓',
  releaseStatusStyles.pending,
  'Unknown',
);

export const getRequestStatusPresentation = (
  status: MediaRequest['status'],
): StatusPresentation => {
  return REQUEST_STATUS_PRESENTATIONS[status] ?? fallbackRequestPresentation;
};

export const getReleaseStatusPresentation = (
  status: Release['status'],
): StatusPresentation => {
  return RELEASE_STATUS_PRESENTATIONS[status] ?? fallbackReleasePresentation;
};
