import type {
  MediaRequest,
  MovieRequest,
  Release,
  ReleaseSearchResult,
  SeriesRequest,
} from '../src/types';

// Mock movie requests
const mockMovieRequests: MovieRequest[] = [
  {
    id: '1',
    type: 'movie',
    title: 'The Dark Knight',
    year: 2008,
    runtime: 152,
    poster_url: 'https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg',
    overview:
      'Batman raises the stakes in his war on crime. With the help of Lt. Jim Gordon and District Attorney Harvey Dent, Batman sets out to dismantle the remaining criminal organizations that plague the streets.',
    genres: ['Action', 'Crime', 'Drama'],
    status: 'completed',
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T14:45:00Z',
    imdb_id: 'tt0468569',
  },
  {
    id: '2',
    type: 'movie',
    title: 'Inception',
    year: 2010,
    runtime: 148,
    poster_url: 'https://image.tmdb.org/t/p/w500/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg',
    overview:
      'Dom Cobb is a skilled thief, the absolute best in the dangerous art of extraction, stealing valuable secrets from deep within the subconscious during the dream state.',
    genres: ['Action', 'Sci-Fi', 'Thriller'],
    status: 'downloading',
    created_at: '2024-01-16T09:15:00Z',
    updated_at: '2024-01-16T12:30:00Z',
    imdb_id: 'tt1375666',
  },
  {
    id: '3',
    type: 'movie',
    title: 'Interstellar',
    year: 2014,
    runtime: 169,
    poster_url: 'https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg',
    overview:
      "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
    genres: ['Adventure', 'Drama', 'Sci-Fi'],
    status: 'searching',
    created_at: '2024-01-17T11:20:00Z',
    updated_at: '2024-01-17T11:25:00Z',
    imdb_id: 'tt0816692',
  },
  {
    id: '4',
    type: 'movie',
    title: 'Dune: Part Two',
    year: 2024,
    runtime: 166,
    poster_url: 'https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg',
    overview:
      'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.',
    genres: ['Action', 'Adventure', 'Sci-Fi'],
    status: 'pending',
    created_at: '2024-01-18T08:45:00Z',
    updated_at: '2024-01-18T08:45:00Z',
    imdb_id: 'tt15239678',
  },
];

// Mock series requests
const mockSeriesRequests: SeriesRequest[] = [
  {
    id: '5',
    type: 'series',
    title: 'Breaking Bad - Season 1',
    year: 2008,
    season_number: 1,
    total_episodes: 7,
    series_title: 'Breaking Bad',
    series_year: 2008,
    poster_url: 'https://image.tmdb.org/t/p/w500/ggFHVNu6YYI5L9pCfOacjizRGt.jpg',
    overview:
      "A high school chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and selling methamphetamine in order to secure his family's future.",
    genres: ['Crime', 'Drama', 'Thriller'],
    status: 'completed',
    created_at: '2024-01-10T14:20:00Z',
    updated_at: '2024-01-10T18:35:00Z',
    imdb_id: 'tt0903747',
  },
  {
    id: '6',
    type: 'series',
    title: 'Breaking Bad - Season 2',
    year: 2009,
    season_number: 2,
    total_episodes: 13,
    series_title: 'Breaking Bad',
    series_year: 2008,
    poster_url: 'https://image.tmdb.org/t/p/w500/ggFHVNu6YYI5L9pCfOacjizRGt.jpg',
    overview:
      'Walt and Jesse attempt to tie up loose ends. The desperate situation gets more complicated with the flip of a coin.',
    genres: ['Crime', 'Drama', 'Thriller'],
    status: 'downloading',
    created_at: '2024-01-12T16:10:00Z',
    updated_at: '2024-01-12T19:25:00Z',
    imdb_id: 'tt0903747',
  },
  {
    id: '7',
    type: 'series',
    title: 'The Last of Us - Season 1',
    year: 2023,
    season_number: 1,
    total_episodes: 9,
    series_title: 'The Last of Us',
    series_year: 2023,
    poster_url: 'https://image.tmdb.org/t/p/w500/uKvVjHNqB5VmOrdxqAt2F7J78ED.jpg',
    overview:
      'Twenty years after modern civilization has been destroyed, Joel, a hardened survivor, is hired to smuggle Ellie, a 14-year-old girl, out of an oppressive quarantine zone.',
    genres: ['Action', 'Adventure', 'Drama'],
    status: 'failed',
    created_at: '2024-01-14T13:30:00Z',
    updated_at: '2024-01-14T15:45:00Z',
    imdb_id: 'tt3581920',
  },
  {
    id: '8',
    type: 'series',
    title: 'House of the Dragon - Season 2',
    year: 2024,
    season_number: 2,
    total_episodes: 8,
    series_title: 'House of the Dragon',
    series_year: 2022,
    poster_url: 'https://image.tmdb.org/t/p/w500/7QMsOTMUswlwxJP0rTTZfmz2tX2.jpg',
    overview: 'The Targaryen civil war continues as both sides prepare for a larger conflict.',
    genres: ['Action', 'Adventure', 'Drama'],
    status: 'searching',
    created_at: '2024-01-19T10:15:00Z',
    updated_at: '2024-01-19T10:20:00Z',
    imdb_id: 'tt11198330',
  },
];

// Mock release search candidates
const mockReleaseSearchResults: ReleaseSearchResult[] = [
  {
    release_id: 't1',
    release_name: 'The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS',
    size: '8.74 GB',
    magnet_link: 'magnet:?xt=urn:btih:example1',
    torrent_file_url: 'https://example.com/torrents/the-dark-knight-1080p.torrent',
    info_url: 'https://example.com/releases/the-dark-knight-1080p',
    seeders: 1247,
    leechers: 23,
    quality: '1080p',
    source: 'SPARKS',
  },
  {
    release_id: 't2',
    release_name: 'The.Dark.Knight.2008.2160p.UHD.BluRay.x265-TERMINAL',
    size: '15.2 GB',
    magnet_link: 'magnet:?xt=urn:btih:example2',
    torrent_file_url: 'https://example.com/torrents/the-dark-knight-2160p.torrent',
    info_url: 'https://example.com/releases/the-dark-knight-2160p',
    seeders: 892,
    leechers: 45,
    quality: '2160p',
    source: 'TERMINAL',
  },
  {
    release_id: 't3',
    release_name: 'The.Dark.Knight.2008.720p.BluRay.x264-YIFY',
    size: '1.2 GB',
    magnet_link: 'magnet:?xt=urn:btih:example3',
    torrent_file_url: 'https://example.com/torrents/the-dark-knight-720p.torrent',
    info_url: 'https://example.com/releases/the-dark-knight-720p',
    seeders: 2156,
    leechers: 67,
    quality: '720p',
    source: 'YIFY',
  },
  {
    release_id: 't4',
    release_name: 'Inception.2010.1080p.BluRay.x264-LEVERAGE',
    size: '7.95 GB',
    magnet_link: 'magnet:?xt=urn:btih:example4',
    torrent_file_url: 'https://example.com/torrents/inception-1080p.torrent',
    info_url: 'https://example.com/releases/inception-1080p',
    seeders: 934,
    leechers: 12,
    quality: '1080p',
    source: 'LEVERAGE',
  },
  {
    release_id: 't5',
    release_name: 'Breaking.Bad.S01.1080p.BluRay.x264-REWARD',
    size: '12.4 GB',
    magnet_link: 'magnet:?xt=urn:btih:example5',
    torrent_file_url: 'https://example.com/torrents/breaking-bad-s01.torrent',
    info_url: 'https://example.com/releases/breaking-bad-s01',
    seeders: 567,
    leechers: 34,
    quality: '1080p',
    source: 'REWARD',
  },
];

// Combine all mock requests
const allMockRequests: MediaRequest[] = [...mockMovieRequests, ...mockSeriesRequests];

export const getMockRequests = async (): Promise<MediaRequest[]> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 500));
  return allMockRequests;
};

export const getMockRequest = async (id: string): Promise<MediaRequest | null> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 300));
  return allMockRequests.find((request) => request.id === id) || null;
};

export const searchMockReleaseSources = async (
  query: string,
  requestId?: string,
): Promise<ReleaseSearchResult[]> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 800));

  if (!query.trim()) {
    return [];
  }

  // Filter releases based on query
  const filteredResults = mockReleaseSearchResults.filter((candidate) =>
    candidate.release_name.toLowerCase().includes(query.toLowerCase()),
  );

  return filteredResults.map((candidate) => ({
    ...candidate,
    ...(requestId ? { request_id: requestId } : {}),
  }));
};

// Mock releases data
const mockReleases: Release[] = [
  {
    id: 'r1',
    name: 'The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS',
    hash: 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0',
    size: 9387654321,
    files: [
      {
        id: 'f1',
        name: 'The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS.mkv',
        size: 9387654321,
        path: '/downloads/The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS/The.Dark.Knight.2008.1080p.BluRay.x264-SPARKS.mkv',
      },
    ],
    status: 'completed',
    progress: 100,
    download_speed: 0,
    upload_speed: 1024000,
    seeders: 1247,
    leechers: 23,
    ratio: 2.5,
    added_date: '2024-01-15T10:30:00Z',
    completed_date: '2024-01-15T14:45:00Z',
    request_ids: ['1'],
    torrent_source: 'SPARKS',
    quality: '1080p',
  },
  {
    id: 'r2',
    name: 'Breaking.Bad.S01.1080p.BluRay.x264-REWARD',
    hash: 'b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1',
    size: 13321123456,
    files: [
      {
        id: 'f2',
        name: 'Breaking.Bad.S01E01.Pilot.1080p.BluRay.x264-REWARD.mkv',
        size: 1903017984,
        path: '/downloads/Breaking.Bad.S01.1080p.BluRay.x264-REWARD/Breaking.Bad.S01E01.Pilot.1080p.BluRay.x264-REWARD.mkv',
      },
      {
        id: 'f3',
        name: "Breaking.Bad.S01E02.Cat's.in.the.Bag.1080p.BluRay.x264-REWARD.mkv",
        size: 1903017984,
        path: "/downloads/Breaking.Bad.S01.1080p.BluRay.x264-REWARD/Breaking.Bad.S01E02.Cat's.in.the.Bag.1080p.BluRay.x264-REWARD.mkv",
      },
      {
        id: 'f4',
        name: "Breaking.Bad.S01E03.And.the.Bag's.in.the.River.1080p.BluRay.x264-REWARD.mkv",
        size: 1903017984,
        path: "/downloads/Breaking.Bad.S01.1080p.BluRay.x264-REWARD/Breaking.Bad.S01E03.And.the.Bag's.in.the.River.1080p.BluRay.x264-REWARD.mkv",
      },
      {
        id: 'f5',
        name: 'Breaking.Bad.S01E04.Cancer.Man.1080p.BluRay.x264-REWARD.mkv',
        size: 1903017984,
        path: '/downloads/Breaking.Bad.S01.1080p.BluRay.x264-REWARD/Breaking.Bad.S01E04.Cancer.Man.1080p.BluRay.x264-REWARD.mkv',
      },
      {
        id: 'f6',
        name: 'Breaking.Bad.S01E05.Gray.Matter.1080p.BluRay.x264-REWARD.mkv',
        size: 1903017984,
        path: '/downloads/Breaking.Bad.S01.1080p.BluRay.x264-REWARD/Breaking.Bad.S01E05.Gray.Matter.1080p.BluRay.x264-REWARD.mkv',
      },
      {
        id: 'f7',
        name: 'Breaking.Bad.S01E06.Crazy.Handful.of.Nothin.1080p.BluRay.x264-REWARD.mkv',
        size: 1903017984,
        path: '/downloads/Breaking.Bad.S01.1080p.BluRay.x264-REWARD/Breaking.Bad.S01E06.Crazy.Handful.of.Nothin.1080p.BluRay.x264-REWARD.mkv',
      },
      {
        id: 'f8',
        name: 'Breaking.Bad.S01E07.A.No-Rough-Stuff-Type.Deal.1080p.BluRay.x264-REWARD.mkv',
        size: 1903017984,
        path: '/downloads/Breaking.Bad.S01.1080p.BluRay.x264-REWARD/Breaking.Bad.S01E07.A.No-Rough-Stuff-Type.Deal.1080p.BluRay.x264-REWARD.mkv',
      },
    ],
    status: 'completed',
    progress: 100,
    download_speed: 0,
    upload_speed: 2048000,
    seeders: 567,
    leechers: 34,
    ratio: 1.8,
    added_date: '2024-01-10T14:20:00Z',
    completed_date: '2024-01-10T18:35:00Z',
    request_ids: ['5'],
    torrent_source: 'REWARD',
    quality: '1080p',
  },
  {
    id: 'r3',
    name: 'Inception.2010.1080p.BluRay.x264-LEVERAGE',
    hash: 'c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2',
    size: 8537676800,
    files: [
      {
        id: 'f9',
        name: 'Inception.2010.1080p.BluRay.x264-LEVERAGE.mkv',
        size: 8537676800,
        path: '/downloads/Inception.2010.1080p.BluRay.x264-LEVERAGE/Inception.2010.1080p.BluRay.x264-LEVERAGE.mkv',
      },
    ],
    status: 'downloading',
    progress: 67,
    download_speed: 5242880,
    upload_speed: 1048576,
    seeders: 934,
    leechers: 12,
    ratio: 0.3,
    added_date: '2024-01-16T09:15:00Z',
    request_ids: ['2'],
    torrent_source: 'LEVERAGE',
    quality: '1080p',
  },
  {
    id: 'r4',
    name: 'Marvel.Collection.2008-2019.1080p.BluRay.x264-COLLECTION',
    hash: 'd4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3',
    size: 234567890123,
    files: [
      {
        id: 'f10',
        name: 'Iron.Man.2008.1080p.BluRay.x264-COLLECTION.mkv',
        size: 8537676800,
        path: '/downloads/Marvel.Collection.2008-2019.1080p.BluRay.x264-COLLECTION/Iron.Man.2008.1080p.BluRay.x264-COLLECTION.mkv',
        request_mapping: {
          request_id: 'req_ironman',
          request_title: 'Iron Man',
          mapping_type: 'movie',
        },
      },
      {
        id: 'f11',
        name: 'The.Incredible.Hulk.2008.1080p.BluRay.x264-COLLECTION.mkv',
        size: 8537676800,
        path: '/downloads/Marvel.Collection.2008-2019.1080p.BluRay.x264-COLLECTION/The.Incredible.Hulk.2008.1080p.BluRay.x264-COLLECTION.mkv',
        request_mapping: {
          request_id: 'req_hulk',
          request_title: 'The Incredible Hulk',
          mapping_type: 'movie',
        },
      },
      {
        id: 'f12',
        name: 'Iron.Man.2.2010.1080p.BluRay.x264-COLLECTION.mkv',
        size: 8537676800,
        path: '/downloads/Marvel.Collection.2008-2019.1080p.BluRay.x264-COLLECTION/Iron.Man.2.2010.1080p.BluRay.x264-COLLECTION.mkv',
        request_mapping: {
          request_id: 'req_ironman2',
          request_title: 'Iron Man 2',
          mapping_type: 'movie',
        },
      },
    ],
    status: 'seeding',
    progress: 100,
    download_speed: 0,
    upload_speed: 3145728,
    seeders: 234,
    leechers: 89,
    ratio: 3.2,
    added_date: '2024-01-05T12:00:00Z',
    completed_date: '2024-01-07T16:30:00Z',
    request_ids: ['req_ironman', 'req_hulk', 'req_ironman2'],
    torrent_source: 'COLLECTION',
    quality: '1080p',
  },
  {
    id: 'r5',
    name: 'Breaking.Bad.Complete.Series.1080p.BluRay.x264-COMPLETE',
    hash: 'e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4',
    size: 456789012345,
    files: [
      {
        id: 'f13',
        name: 'Breaking.Bad.S02E01.Seven.Thirty-Seven.1080p.BluRay.x264-COMPLETE.mkv',
        size: 1903017984,
        path: '/downloads/Breaking.Bad.Complete.Series.1080p.BluRay.x264-COMPLETE/Season.02/Breaking.Bad.S02E01.Seven.Thirty-Seven.1080p.BluRay.x264-COMPLETE.mkv',
        request_mapping: {
          request_id: '6',
          request_title: 'Breaking Bad - Season 2',
          mapping_type: 'series',
          season: 2,
          episode: 1,
        },
      },
      {
        id: 'f14',
        name: 'Breaking.Bad.S02E02.Grilled.1080p.BluRay.x264-COMPLETE.mkv',
        size: 1903017984,
        path: '/downloads/Breaking.Bad.Complete.Series.1080p.BluRay.x264-COMPLETE/Season.02/Breaking.Bad.S02E02.Grilled.1080p.BluRay.x264-COMPLETE.mkv',
        request_mapping: {
          request_id: '6',
          request_title: 'Breaking Bad - Season 2',
          mapping_type: 'series',
          season: 2,
          episode: 2,
        },
      },
    ],
    status: 'downloading',
    progress: 23,
    download_speed: 3145728,
    upload_speed: 524288,
    seeders: 445,
    leechers: 156,
    ratio: 0.1,
    added_date: '2024-01-12T16:10:00Z',
    request_ids: ['5', '6'],
    torrent_source: 'COMPLETE',
    quality: '1080p',
  },
];

export const getMockReleases = async (): Promise<Release[]> => {
  await new Promise((resolve) => setTimeout(resolve, 400));
  return mockReleases;
};

export const getMockRelease = async (id: string): Promise<Release | null> => {
  await new Promise((resolve) => setTimeout(resolve, 300));
  return mockReleases.find((release) => release.id === id) || null;
};

export const getMockReleasesByRequest = async (requestId: string): Promise<Release[]> => {
  await new Promise((resolve) => setTimeout(resolve, 350));
  return mockReleases.filter((release) => release.request_ids.includes(requestId));
};

