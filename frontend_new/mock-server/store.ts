import {
  getMockReleases,
  getMockRequests,
  searchMockReleaseSources,
} from './mockData';
import type {
  MediaRequest,
  Release,
  ReleaseFile,
  ReleaseSearchResult,
} from '../src/types';

type RequestStatus = MediaRequest['status'];
type RequestType = MediaRequest['type'];
type ReleaseStatus = Release['status'];

type NewMediaRequestPayload = {
  type: RequestType;
  title: string;
  year: number;
  poster_url?: string;
  overview?: string;
  genres?: string[];
  imdb_id?: string;
  runtime?: number;
  season_number?: number;
  total_episodes?: number;
  series_title?: string;
  series_year?: number;
};

type UpdateMediaRequestPayload = Partial<NewMediaRequestPayload> & {
  status?: RequestStatus;
};

type NewReleasePayload = {
  magnet_link: string;
  request_ids: string[];
};

type UpdateFileMappingPayload = {
  file_id: string;
  request_mapping?: ReleaseFile['request_mapping'];
};

const DEFAULT_POSTER = (title: string) =>
  `https://via.placeholder.com/300x450.png?text=${encodeURIComponent(title)}`;

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value));

const randomId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2);
};

export class MockStore {
  private requestsCache: MediaRequest[] | null = null;
  private releasesCache: Release[] | null = null;

  private async ensureRequests(): Promise<MediaRequest[]> {
    if (!this.requestsCache) {
      const requests = await getMockRequests();
      this.requestsCache = requests.map((request) => clone(request));
    }
    return this.requestsCache;
  }

  private async ensureReleases(): Promise<Release[]> {
    if (!this.releasesCache) {
      const releases = await getMockReleases();
      this.releasesCache = releases.map((release) => clone(release));
    }
    return this.releasesCache;
  }

  async listRequests(filters: {
    status?: RequestStatus;
    type?: RequestType;
  } = {}): Promise<MediaRequest[]> {
    const { status, type } = filters;
    const requests = await this.ensureRequests();

    let result = requests;
    if (status) {
      result = result.filter((request) => request.status === status);
    }
    if (type) {
      result = result.filter((request) => request.type === type);
    }

    return result.map((request) => clone(request));
  }

  async getRequest(id: string): Promise<MediaRequest | null> {
    const requests = await this.ensureRequests();
    const request = requests.find((item) => item.id === id);
    return request ? clone(request) : null;
  }

  async createRequest(payload: NewMediaRequestPayload): Promise<MediaRequest> {
    const requests = await this.ensureRequests();

    if (payload.type === 'movie') {
      if (typeof payload.runtime !== 'number' || !payload.imdb_id) {
        throw new Error('Movie requests require runtime and imdb_id');
      }
    }

    if (payload.type === 'series') {
      if (
        typeof payload.season_number !== 'number' ||
        typeof payload.total_episodes !== 'number' ||
        !payload.series_title ||
        typeof payload.series_year !== 'number' ||
        !payload.imdb_id
      ) {
        throw new Error(
          'Series requests require season, episode counts, series metadata, and imdb_id',
        );
      }
    }

    const now = new Date().toISOString();
    const base = {
      id: randomId(),
      title: payload.title,
      year: payload.year,
      poster_url: payload.poster_url || DEFAULT_POSTER(payload.title),
      overview: payload.overview || 'No overview provided.',
      genres: payload.genres || [],
      status: 'pending' as RequestStatus,
      created_at: now,
      updated_at: now,
    };

    let request: MediaRequest;
    if (payload.type === 'movie') {
      request = {
        ...base,
        type: 'movie',
        runtime: payload.runtime!,
        imdb_id: payload.imdb_id!,
      };
    } else {
      request = {
        ...base,
        type: 'series',
        season_number: payload.season_number!,
        total_episodes: payload.total_episodes!,
        series_title: payload.series_title!,
        series_year: payload.series_year!,
        imdb_id: payload.imdb_id!,
      };
    }

    requests.unshift(request);
    return clone(request);
  }

  async updateRequest(id: string, payload: UpdateMediaRequestPayload): Promise<MediaRequest | null> {
    const requests = await this.ensureRequests();
    const request = requests.find((item) => item.id === id);
    if (!request) {
      return null;
    }

    if (payload.title) request.title = payload.title;
    if (payload.year) request.year = payload.year;
    if (payload.poster_url) request.poster_url = payload.poster_url;
    if (payload.overview) request.overview = payload.overview;
    if (payload.genres) request.genres = payload.genres;
    if (payload.status) request.status = payload.status;

    if (request.type === 'movie') {
      if (typeof payload.runtime === 'number') request.runtime = payload.runtime;
      if (payload.imdb_id) request.imdb_id = payload.imdb_id;
    } else {
      if (typeof payload.season_number === 'number') request.season_number = payload.season_number;
      if (typeof payload.total_episodes === 'number') request.total_episodes = payload.total_episodes;
      if (payload.series_title) request.series_title = payload.series_title;
      if (typeof payload.series_year === 'number') request.series_year = payload.series_year;
      if (payload.imdb_id) request.imdb_id = payload.imdb_id;
    }

    request.updated_at = new Date().toISOString();
    return clone(request);
  }

  async deleteRequest(id: string): Promise<boolean> {
    const requests = await this.ensureRequests();
    const index = requests.findIndex((item) => item.id === id);
    if (index === -1) {
      return false;
    }
    requests.splice(index, 1);
    return true;
  }

  async listReleases(filters: {
    status?: ReleaseStatus;
    requestId?: string;
  } = {}): Promise<Release[]> {
    const releases = await this.ensureReleases();
    let result = releases;

    if (filters.status) {
      result = result.filter((release) => release.status === filters.status);
    }
    if (filters.requestId) {
      result = result.filter((release) => release.request_ids.includes(filters.requestId!));
    }

    return result.map((release) => clone(release));
  }

  async getRelease(id: string): Promise<Release | null> {
    const releases = await this.ensureReleases();
    const release = releases.find((item) => item.id === id);
    return release ? clone(release) : null;
  }

  async addRelease(payload: NewReleasePayload): Promise<Release> {
    const releases = await this.ensureReleases();
    const now = new Date();
    const newRelease: Release = {
      id: randomId(),
      name: `Manual-${now.getTime()}`,
      hash: randomId().replace(/-/g, ''),
      size: 0,
      files: [
        {
          id: randomId(),
          name: 'placeholder.mkv',
          size: 0,
          path: '/downloads/placeholder.mkv',
        },
      ],
      status: 'pending',
      progress: 0,
      download_speed: 0,
      upload_speed: 0,
      seeders: 0,
      leechers: 0,
      ratio: 0,
      added_date: now.toISOString(),
      request_ids: payload.request_ids,
      torrent_source: 'manual',
      quality: 'unknown',
    };

    releases.unshift(newRelease);
    return clone(newRelease);
  }

  async deleteRelease(id: string): Promise<boolean> {
    const releases = await this.ensureReleases();
    const index = releases.findIndex((item) => item.id === id);
    if (index === -1) {
      return false;
    }
    releases.splice(index, 1);
    return true;
  }

  async pauseRelease(id: string): Promise<boolean> {
    const releases = await this.ensureReleases();
    const release = releases.find((item) => item.id === id);
    if (!release) return false;
    if (release.status === 'completed') return false;
    release.status = 'pending';
    release.progress = Math.min(release.progress, 99);
    release.download_speed = 0;
    return true;
  }

  async resumeRelease(id: string): Promise<boolean> {
    const releases = await this.ensureReleases();
    const release = releases.find((item) => item.id === id);
    if (!release) return false;
    release.status = 'downloading';
    if (release.progress < 5) {
      release.progress = 5;
    }
    release.download_speed = Math.max(release.download_speed, 1024 * 1024);
    return true;
  }

  async updateFileMappings(
    releaseId: string,
    mappings: UpdateFileMappingPayload[],
  ): Promise<boolean> {
    const releases = await this.ensureReleases();
    const release = releases.find((item) => item.id === releaseId);
    if (!release) return false;
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return false;
    }

    let success = true;

    mappings.forEach((mapping) => {
      const file = release.files.find((item) => item.id === mapping.file_id);
      if (!file) {
        success = false;
        return;
      }

      if (mapping.request_mapping) {
        const requestMapping = clone(mapping.request_mapping);
        requestMapping.mapping_type =
          requestMapping.mapping_type === 'movie' ? 'movie' : 'series';
        if (requestMapping.mapping_type === 'movie') {
          delete requestMapping.season;
          delete requestMapping.episode;
        } else {
          if (typeof requestMapping.season !== 'number' || requestMapping.season <= 0) {
            requestMapping.season = 1;
          }
          if (typeof requestMapping.episode !== 'number' || requestMapping.episode <= 0) {
            requestMapping.episode = 1;
          }
        }
        file.request_mapping = requestMapping;
      }
      if (mapping.request_mapping === null) {
        file.request_mapping = undefined;
      }
    });

    return success;
  }

  async searchReleaseCandidates(query: string): Promise<ReleaseSearchResult[]> {
    const results = await searchMockReleaseSources(query);
    return results.map((result) => clone(result));
  }
}

export const mockStore = new MockStore();
