import type { ReleaseFile } from '@/types';

const VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'];
const SUBTITLE_EXTENSIONS = ['.srt', '.ass', '.ssa', '.sub', '.vtt', '.idx'];

const extensionOf = (filename: string): string => {
  const index = filename.lastIndexOf('.');
  return index === -1 ? '' : filename.slice(index).toLowerCase();
};

export const isVideoFile = (filename: string): boolean =>
  VIDEO_EXTENSIONS.includes(extensionOf(filename));

export const isSubtitleFile = (filename: string): boolean =>
  SUBTITLE_EXTENSIONS.includes(extensionOf(filename));

/** Natural ordering so `E9` sorts before `E10`. */
export const compareByFileName = (a: ReleaseFile, b: ReleaseFile): number =>
  a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' });

export interface GroupedFiles {
  video: ReleaseFile[];
  subtitle: ReleaseFile[];
  other: ReleaseFile[];
}

export const groupFilesByType = (files: ReleaseFile[]): GroupedFiles =>
  files.reduce<GroupedFiles>(
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
    { video: [], subtitle: [], other: [] },
  );

export interface SplitFiles {
  video: ReleaseFile[];
  other: ReleaseFile[];
}

/**
 * Videos are what these listings are read for; subtitles, samples and NFOs all
 * land in one `other` bucket. Both sides come back sorted by name.
 */
export const splitVideoFiles = (files: ReleaseFile[]): SplitFiles => {
  const video: ReleaseFile[] = [];
  const other: ReleaseFile[] = [];

  files.forEach((file) => {
    (isVideoFile(file.name) ? video : other).push(file);
  });

  return { video: video.sort(compareByFileName), other: other.sort(compareByFileName) };
};

export const formatEpisodeCode = (season: number, episode: number): string =>
  `S${String(season).padStart(2, '0')}E${String(episode).padStart(2, '0')}`;
