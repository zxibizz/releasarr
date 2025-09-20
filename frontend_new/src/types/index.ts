// Core request types
export interface BaseRequest {
  id: string;
  title: string;
  year: number;
  poster_url: string;
  overview: string;
  genres: string[];
  status: 'pending' | 'searching' | 'downloading' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface MovieRequest extends BaseRequest {
  type: 'movie';
  runtime: number;
  imdb_id: string;
}

export interface SeriesRequest extends BaseRequest {
  type: 'series';
  season_number: number;
  total_episodes: number;
  series_title: string;
  series_year: number;
  imdb_id: string;
}

export type MediaRequest = MovieRequest | SeriesRequest;

// Release types
export interface ReleaseFile {
  id: string;
  name: string;
  size: number;
  path: string;
  episode_mapping?: EpisodeMapping;
  request_mapping?: FileRequestMapping;
}

export interface EpisodeMapping {
  season: number;
  episode: number;
  title?: string;
}

export interface FileRequestMapping {
  request_id: string;
  request_title: string;
  mapping_type: 'episode' | 'movie' | 'season';
  season?: number;
  episode?: number;
}

export interface Release {
  id: string;
  name: string;
  hash: string;
  size: number;
  files: ReleaseFile[];
  status: 'pending' | 'downloading' | 'seeding' | 'completed' | 'failed';
  progress: number;
  download_speed: number;
  upload_speed: number;
  seeders: number;
  leechers: number;
  ratio: number;
  added_date: string;
  completed_date?: string;
  request_ids: string[];
  torrent_source?: string;
  quality?: string;
}

export interface ReleaseStats {
  total_releases: number;
  active_downloads: number;
  completed_releases: number;
  total_size: number;
  total_uploaded: number;
  total_downloaded: number;
}

// Torrent search types
export interface TorrentResult {
  id: string;
  name: string;
  size: string;
  link: string;
  seeders: number;
  leechers: number;
  quality: string;
  source: string;
}

export interface SearchState {
  query: string;
  results: TorrentResult[];
  loading: boolean;
  error: string | null;
}

// API response types
export interface RequestsResponse {
  requests: MediaRequest[];
  total: number;
  page: number;
  per_page: number;
}

export interface TorrentSearchResponse {
  results: TorrentResult[];
  query: string;
  total_results: number;
}
