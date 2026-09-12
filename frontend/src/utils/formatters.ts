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
  return `${Number.parseFloat(size.toFixed(precision))} ${FILE_SIZE_UNITS[unitIndex]}`;
};

export const formatSpeed = (bytesPerSecond: number): string => `${formatFileSize(bytesPerSecond)}/s`;

export const formatProgress = (progress: number): string => `${progress.toFixed(1)}%`;

export const formatRatio = (ratio: number): string => ratio.toFixed(2);

export const formatDuration = (seconds: number): string => {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return 'Unknown';
  }
  if (seconds < 60) {
    return `${Math.floor(seconds)}s`;
  }
  if (seconds < 3600) {
    return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  }
  if (seconds < 86400) {
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  }
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
};

export const calculateEta = (
  totalBytes: number,
  downloadedBytes: number,
  bytesPerSecond: number,
): string | null => {
  if (bytesPerSecond <= 0) {
    return null;
  }
  return formatDuration((totalBytes - downloadedBytes) / bytesPerSecond);
};

export const formatRuntime = (minutes: number): string => {
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  return hours === 0 ? `${remaining}m` : `${hours}h ${remaining}m`;
};

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
});

const safeFormat = (value: string | number, formatter: Intl.DateTimeFormat): string => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : formatter.format(date);
};

export const formatDate = (value: string | number): string => safeFormat(value, dateFormatter);

export const formatDateTime = (value: string | number): string =>
  safeFormat(value, dateTimeFormatter);
