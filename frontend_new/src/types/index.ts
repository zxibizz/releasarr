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
