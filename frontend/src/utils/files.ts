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

export interface ParsedEpisode {
  season?: number;
  episode?: number;
}

const SEASON_EPISODE_PATTERNS = [
  /(?<![a-z0-9])s(\d{1,3})[\s._-]*e(\d{1,3})(?!\d)/i,
  /season[\s._-]*(\d{1,3})[\s._-]*(?:episode|ep)[\s._-]*(\d{1,3})(?!\d)/i,
  // `2x05`. The trailing guard keeps resolutions such as `1920x1080` out.
  /(?<![a-z0-9])(\d{1,2})x(\d{1,3})(?![\dip])/i,
];

const SEASON_PATTERN = /(?<![a-z0-9])(?:season|series|saison|temporada|s)[\s._-]*(\d{1,3})(?!\d)/i;
const EPISODE_PATTERN = /(?<![a-z0-9])(?:episode|ep|e)[\s._-]*(\d{1,3})(?!\d)/i;

/** A bare number surrounded by separators, e.g. `Avatar - 07 [1080p].mkv`. */
const LOOSE_EPISODE_PATTERN = /(?:(?<=^)|(?<=[\s._\-[(]))(\d{1,3})(?=[\s._\-\])]|$)/g;

/** Quality/codec/audio tokens that would otherwise read as loose episode numbers. */
const JUNK_PATTERN = new RegExp(
  '(?<![a-z0-9])(?:' +
    '\\d{3,4}[pi]' +
    '|\\d{3,4}x\\d{3,4}' +
    '|[xh][\\s._-]?26[45]' +
    '|hevc|avc|xvid|divx|10bit|8bit|hdr10?|dv|sdr' +
    '|(?:19|20)\\d{2}' +
    '|(?:dd\\+?|ddp|ac3|eac3|aac|dts(?:[\\s._-]?hd)?|truehd|atmos|flac|mp3|opus)' +
    '(?:[\\s._-]?\\d(?:[\\s._-]?\\d)?)?' +
    '|[257][\\s._-]?1(?:ch)?' +
    '|web[\\s._-]?dl|webrip|web|bluray|blu[\\s._-]?ray|bdrip|brrip|bdremux|remux' +
    '|hdtv|dvdrip|dvd|hdrip|amzn|nf|dsnp|hmax|atvp' +
    '|repack|proper|extended|uncut|complete|multi|dual|dubbed|subbed' +
    '|v\\d' +
    ')(?![a-z0-9])',
  'gi',
);

const MAX_SEASON = 100;
const MAX_EPISODE = 999;

const stripExtension = (filename: string): string => {
  const index = filename.lastIndexOf('.');
  return index === -1 ? filename : filename.slice(0, index);
};

const matchNumber = (text: string, pattern: RegExp): number | undefined => {
  const match = text.match(pattern);
  return match ? Number.parseInt(match[1], 10) : undefined;
};

const inRange = (value: number | undefined, max: number): number | undefined =>
  value !== undefined && value > 0 && value <= max ? value : undefined;

const segmentsOf = (path: string): string[] =>
  path.replace(/\\/g, '/').split('/').filter(Boolean);

const seasonFromDirectories = (directories: string[]): number | undefined => {
  for (const directory of [...directories].reverse()) {
    const season = matchNumber(directory, SEASON_PATTERN);
    if (season !== undefined) {
      return season;
    }
  }
  return undefined;
};

/** Reads a bare number as the episode, but only when it is unambiguous. */
const looseEpisode = (stem: string): number | undefined => {
  const cleaned = stem.replace(JUNK_PATTERN, ' ');
  const candidates = new Set(
    [...cleaned.matchAll(LOOSE_EPISODE_PATTERN)].map((match) => Number.parseInt(match[1], 10)),
  );
  return candidates.size === 1 ? [...candidates][0] : undefined;
};

const parse = (filename: string, directories: string[]): ParsedEpisode => {
  const stem = stripExtension(filename);

  for (const pattern of SEASON_EPISODE_PATTERNS) {
    const match = stem.match(pattern);
    if (match) {
      return {
        season: inRange(Number.parseInt(match[1], 10), MAX_SEASON),
        episode: inRange(Number.parseInt(match[2], 10), MAX_EPISODE),
      };
    }
  }

  // Dropping the matched season text stops `Season 2` from later reading as episode 2.
  const seasonMatch = stem.match(SEASON_PATTERN);
  const remainder = seasonMatch ? stem.replace(SEASON_PATTERN, ' ') : stem;
  const season = seasonMatch
    ? Number.parseInt(seasonMatch[1], 10)
    : seasonFromDirectories(directories);

  let episode = matchNumber(remainder, EPISODE_PATTERN);
  if (episode === undefined && season !== undefined) {
    episode = looseEpisode(remainder);
  }

  return { season: inRange(season, MAX_SEASON), episode: inRange(episode, MAX_EPISODE) };
};

/** Best-effort season/episode extraction from a release file name. */
export const parseEpisodeFromFilename = (filename: string): ParsedEpisode => parse(filename, []);

/**
 * Like {@link parseEpisodeFromFilename} but falls back to the enclosing folders
 * for the season, which is how most multi-season packs are laid out
 * (`Season 02/Show - 05.mkv`).
 */
export const parseEpisodeFromFile = (file: Pick<ReleaseFile, 'name' | 'path'>): ParsedEpisode => {
  // `name` may itself be a relative path, as torrent file listings usually are.
  const nameSegments = segmentsOf(file.name);
  const directories = (file.path ? segmentsOf(file.path) : nameSegments).slice(0, -1);
  return parse(nameSegments[nameSegments.length - 1] ?? '', directories);
};

export const formatEpisodeCode = (season: number, episode: number): string =>
  `S${String(season).padStart(2, '0')}E${String(episode).padStart(2, '0')}`;
