import { format, parseISO } from 'date-fns';

const FILE_SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];

export const formatFileSize = (rawBytes: number): string => {
  const bytes = Number.isFinite(rawBytes) ? Math.max(0, rawBytes) : 0;
  if (bytes === 0) {
    return '0 B';
  }

  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < FILE_SIZE_UNITS.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  const precision = unitIndex === 0 ? 0 : size >= 10 ? 1 : 2;
  const formatted = Number.parseFloat(size.toFixed(precision));

  return `${formatted} ${FILE_SIZE_UNITS[unitIndex]}`;
};

export const formatDate = (dateString: string): string => {
  try {
    const date = parseISO(dateString);
    return format(date, 'MMM dd, yyyy');
  } catch {
    return dateString;
  }
};

export const formatDateTime = (dateString: string): string => {
  try {
    const date = parseISO(dateString);
    return format(date, 'MMM dd, yyyy HH:mm');
  } catch {
    return dateString;
  }
};

export const formatRuntime = (minutes: number): string => {
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (hours === 0) {
    return `${remainingMinutes}m`;
  }

  return `${hours}h ${remainingMinutes}m`;
};
