import type { MediaRequest, Release, RequestLogEntry } from '@/types';

type StatusStyle = {
  bg: string;
  color: string;
  borderColor: string;
};

const sharedStatusStyles: Record<string, StatusStyle> = {
  pending: {
    bg: 'status.pending.bg',
    color: 'status.pending.fg',
    borderColor: 'status.pending.border',
  },
  searching: {
    bg: 'status.searching.bg',
    color: 'status.searching.fg',
    borderColor: 'status.searching.border',
  },
  downloading: {
    bg: 'status.downloading.bg',
    color: 'status.downloading.fg',
    borderColor: 'status.downloading.border',
  },
  completed: {
    bg: 'status.completed.bg',
    color: 'status.completed.fg',
    borderColor: 'status.completed.border',
  },
  failed: {
    bg: 'status.failed.bg',
    color: 'status.failed.fg',
    borderColor: 'status.failed.border',
  },
  seeding: {
    bg: 'status.seeding.bg',
    color: 'status.seeding.fg',
    borderColor: 'status.seeding.border',
  },
};

export const requestStatusStyles: Record<MediaRequest['status'], StatusStyle> = {
  pending: sharedStatusStyles.pending,
  searching: sharedStatusStyles.searching,
  downloading: sharedStatusStyles.downloading,
  completed: sharedStatusStyles.completed,
  failed: sharedStatusStyles.failed,
};

export const releaseStatusStyles: Record<Release['status'], StatusStyle> = {
  pending: sharedStatusStyles.pending,
  downloading: sharedStatusStyles.downloading,
  seeding: sharedStatusStyles.seeding,
  completed: sharedStatusStyles.completed,
  failed: sharedStatusStyles.failed,
};

export const getStatusStyle = (status: string): StatusStyle => {
  return (
    sharedStatusStyles[status] ?? {
      bg: 'status.searching.bg',
      color: 'status.searching.fg',
      borderColor: 'status.searching.border',
    }
  );
};

export const logLevelStyles: Record<RequestLogEntry['level'], StatusStyle> = {
  info: {
    bg: 'status.info.bg',
    color: 'status.info.fg',
    borderColor: 'status.info.border',
  },
  warning: {
    bg: 'status.warning.bg',
    color: 'status.warning.fg',
    borderColor: 'status.warning.border',
  },
  error: {
    bg: 'status.error.bg',
    color: 'status.error.fg',
    borderColor: 'status.error.border',
  },
};
