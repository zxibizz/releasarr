import { EpisodeMapping, FileRequestMapping, Release, ReleaseFile } from '../types';

export const formatFileSize = (bytes: number): string => {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
};

export const formatSpeed = (bytesPerSecond: number): string => {
  return `${formatFileSize(bytesPerSecond)}/s`;
};

export const formatRatio = (ratio: number): string => {
  return ratio.toFixed(2);
};

export const formatProgress = (progress: number): string => {
  return `${progress.toFixed(1)}%`;
};

export const formatDuration = (seconds: number): string => {
  if (seconds < 60) {
    return `${Math.floor(seconds)}s`;
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  } else if (seconds < 86400) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  } else {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    return `${days}d ${hours}h`;
  }
};

export const calculateETA = (totalSize: number, downloadedSize: number, speed: number): string => {
  if (speed === 0) return 'Unknown';
  
  const remainingBytes = totalSize - downloadedSize;
  const remainingSeconds = remainingBytes / speed;
  
  return formatDuration(remainingSeconds);
};

export const getStatusColor = (status: Release['status']): string => {
  switch (status) {
    case 'pending':
      return 'text-yellow-600 bg-yellow-100';
    case 'downloading':
      return 'text-blue-600 bg-blue-100';
    case 'seeding':
      return 'text-green-600 bg-green-100';
    case 'completed':
      return 'text-green-700 bg-green-200';
    case 'failed':
      return 'text-red-600 bg-red-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

export const getStatusIcon = (status: Release['status']): string => {
  switch (status) {
    case 'pending':
      return '⏳';
    case 'downloading':
      return '⬇️';
    case 'seeding':
      return '⬆️';
    case 'completed':
      return '✅';
    case 'failed':
      return '❌';
    default:
      return '❓';
  }
};

export const sortReleasesByStatus = (releases: Release[]): Release[] => {
  const statusOrder = ['downloading', 'pending', 'seeding', 'completed', 'failed'];
  
  return [...releases].sort((a, b) => {
    const aIndex = statusOrder.indexOf(a.status);
    const bIndex = statusOrder.indexOf(b.status);
    
    if (aIndex !== bIndex) {
      return aIndex - bIndex;
    }
    
    return new Date(b.added_date).getTime() - new Date(a.added_date).getTime();
  });
};

export const sortReleasesByDate = (releases: Release[], ascending: boolean = false): Release[] => {
  return [...releases].sort((a, b) => {
    const dateA = new Date(a.added_date).getTime();
    const dateB = new Date(b.added_date).getTime();
    
    return ascending ? dateA - dateB : dateB - dateA;
  });
};

export const sortReleasesBySize = (releases: Release[], ascending: boolean = false): Release[] => {
  return [...releases].sort((a, b) => {
    return ascending ? a.size - b.size : b.size - a.size;
  });
};

export const filterReleasesByStatus = (releases: Release[], status: Release['status']): Release[] => {
  return releases.filter(release => release.status === status);
};

export const filterReleasesByRequest = (releases: Release[], requestId: string): Release[] => {
  return releases.filter(release => release.request_ids.includes(requestId));
};

export const getActiveDownloads = (releases: Release[]): Release[] => {
  return releases.filter(release => release.status === 'downloading');
};

export const getCompletedReleases = (releases: Release[]): Release[] => {
  return releases.filter(release => release.status === 'completed' || release.status === 'seeding');
};

export const getTotalDownloadSpeed = (releases: Release[]): number => {
  return releases
    .filter(release => release.status === 'downloading')
    .reduce((total, release) => total + release.download_speed, 0);
};

export const getTotalUploadSpeed = (releases: Release[]): number => {
  return releases
    .filter(release => release.status === 'seeding' || release.status === 'completed')
    .reduce((total, release) => total + release.upload_speed, 0);
};

export const getTotalSize = (releases: Release[]): number => {
  return releases.reduce((total, release) => total + release.size, 0);
};

export const hasEpisodeMapping = (file: ReleaseFile): boolean => {
  return !!file.episode_mapping;
};

export const hasRequestMapping = (file: ReleaseFile): boolean => {
  return !!file.request_mapping;
};

export const getFilesByEpisode = (files: ReleaseFile[], season: number, episode: number): ReleaseFile[] => {
  return files.filter(file => 
    file.episode_mapping?.season === season && 
    file.episode_mapping?.episode === episode
  );
};

export const getFilesByRequest = (files: ReleaseFile[], requestId: string): ReleaseFile[] => {
  return files.filter(file => file.request_mapping?.request_id === requestId);
};

export const getUnmappedFiles = (files: ReleaseFile[]): ReleaseFile[] => {
  return files.filter(file => !file.episode_mapping && !file.request_mapping);
};

export const formatEpisodeString = (mapping: EpisodeMapping): string => {
  const seasonStr = mapping.season.toString().padStart(2, '0');
  const episodeStr = mapping.episode.toString().padStart(2, '0');
  return `S${seasonStr}E${episodeStr}`;
};

export const formatEpisodeTitle = (mapping: EpisodeMapping): string => {
  const episodeStr = formatEpisodeString(mapping);
  return mapping.title ? `${episodeStr} - ${mapping.title}` : episodeStr;
};

export const parseEpisodeFromFilename = (filename: string): EpisodeMapping | null => {
  const patterns = [
    /S(\d{1,2})E(\d{1,2})/i,
    /Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})/i,
    /(\d{1,2})x(\d{1,2})/i,
  ];

  for (const pattern of patterns) {
    const match = filename.match(pattern);
    if (match) {
      return {
        season: parseInt(match[1], 10),
        episode: parseInt(match[2], 10),
      };
    }
  }

  return null;
};

export const suggestEpisodeMapping = (file: ReleaseFile): EpisodeMapping | null => {
  return parseEpisodeFromFilename(file.name);
};

export const validateEpisodeMapping = (mapping: EpisodeMapping): boolean => {
  return (
    mapping.season > 0 &&
    mapping.episode > 0 &&
    mapping.season <= 99 &&
    mapping.episode <= 999
  );
};

export const validateRequestMapping = (mapping: FileRequestMapping): boolean => {
  if (!mapping.request_id || !mapping.request_title || !mapping.mapping_type) {
    return false;
  }

  if (!['movie', 'series'].includes(mapping.mapping_type)) {
    return false;
  }

  if (mapping.mapping_type === 'series') {
    if (mapping.season === undefined || mapping.episode === undefined) {
      return false;
    }
    if (mapping.season !== undefined && mapping.season <= 0) {
      return false;
    }
    if (mapping.episode !== undefined && mapping.episode <= 0) {
      return false;
    }
  }

  return true;
};

export const isVideoFile = (filename: string): boolean => {
  const videoExtensions = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'];
  const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
  return videoExtensions.includes(extension);
};

export const isSubtitleFile = (filename: string): boolean => {
  const subtitleExtensions = ['.srt', '.ass', '.ssa', '.sub', '.vtt', '.idx'];
  const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
  return subtitleExtensions.includes(extension);
};

export const groupFilesByType = (files: ReleaseFile[]): { video: ReleaseFile[]; subtitle: ReleaseFile[]; other: ReleaseFile[] } => {
  return files.reduce(
    (groups, file) => {
      if (isVideoFile(file.name)) {
        groups.video.push(file);
      } else if (isSubtitleFile(file.name)) {
        groups.subtitle.push(file);
      } else {
        groups.other.push(file);
      }
      return groups;
    },
    { video: [] as ReleaseFile[], subtitle: [] as ReleaseFile[], other: [] as ReleaseFile[] }
  );
};

export const calculateReleaseProgress = (release: Release): number => {
  if (release.status === 'completed' || release.status === 'seeding') {
    return 100;
  }
  return release.progress;
};

export const isReleaseComplete = (release: Release): boolean => {
  return release.status === 'completed' || release.status === 'seeding';
};

export const isReleaseActive = (release: Release): boolean => {
  return release.status === 'downloading' || release.status === 'pending';
};

export const getReleaseHealthScore = (release: Release): number => {
  const seeders = release.seeders;
  const leechers = release.leechers;
  
  if (seeders === 0) return 0;
  if (leechers === 0) return 100;
  
  const ratio = seeders / (seeders + leechers);
  return Math.round(ratio * 100);
};

export const getHealthColor = (healthScore: number): string => {
  if (healthScore >= 80) return 'text-green-600';
  if (healthScore >= 50) return 'text-yellow-600';
  if (healthScore >= 20) return 'text-orange-600';
  return 'text-red-600';
};
