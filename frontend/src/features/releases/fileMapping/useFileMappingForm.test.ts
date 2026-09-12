import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useFileMappingForm } from '@/features/releases/fileMapping/useFileMappingForm';
import type { MediaRequest, ReleaseFile } from '@/types';

const files: ReleaseFile[] = [
  { id: 'f1', name: 'Show.S02E01.1080p.mkv', size: 100, path: '/downloads/f1.mkv' },
  { id: 'f2', name: 'Show.S02E02.1080p.mkv', size: 200, path: '/downloads/f2.mkv' },
  { id: 'f3', name: 'readme.txt', size: 10, path: '/downloads/readme.txt' },
];

const seriesRequest: MediaRequest = {
  id: 'req-1',
  type: 'series',
  title: 'Show',
  year: 2024,
  season_number: 2,
  total_episodes: 10,
  series_title: 'Show',
  series_year: 2024,
  imdb_id: 'tt1',
  poster_url: 'https://example.test/p.jpg',
  overview: '',
  genres: [],
  status: 'downloading',
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: '2026-01-01T00:00:00.000Z',
};

const seasonRequest = (id: string, seasonNumber: number): MediaRequest => ({
  ...seriesRequest,
  id,
  title: `Avatar - Season ${seasonNumber}`,
  season_number: seasonNumber,
  series_title: 'Avatar',
  sonarr_series_id: 42,
});

const packFiles: ReleaseFile[] = [
  { id: 'p1', name: 'Avatar.S01E01.mkv', size: 1, path: 'Avatar/Avatar.S01E01.mkv' },
  { id: 'p2', name: 'Avatar.S02E01.mkv', size: 1, path: 'Avatar/Avatar.S02E01.mkv' },
  { id: 'p3', name: '01 - The Awakening.mkv', size: 1, path: 'Avatar/Season 3/01 - The Awakening.mkv' },
];

const packRequests = [seasonRequest('req-s1', 1), seasonRequest('req-s2', 2), seasonRequest('req-s3', 3)];

const packDefault = {
  id: 'req-s1',
  title: 'Avatar - Season 1',
  type: 'series' as const,
  seasonNumber: 1,
  seriesTitle: 'Avatar',
  sonarrSeriesId: 42,
};

describe('useFileMappingForm', () => {
  it('starts with empty drafts and no pending changes', () => {
    const { result } = renderHook(() => useFileMappingForm(files));

    expect(result.current.getDraft('f1').requestId).toBe('');
    expect(result.current.dirtyFileIds).toEqual([]);
    expect(result.current.buildPayload(files)).toEqual([]);
  });

  it('applies a series request to every file and parses season/episode', () => {
    const { result } = renderHook(() => useFileMappingForm(files));

    act(() => result.current.applyToAll(seriesRequest, files));

    expect(result.current.getDraft('f1')).toMatchObject({
      requestId: 'req-1',
      mappingType: 'series',
      season: 2,
      episode: 1,
    });
    expect(result.current.getDraft('f2')).toMatchObject({ season: 2, episode: 2 });
    expect(result.current.dirtyFileIds).toHaveLength(3);
  });

  it('serialises series mappings into the API payload shape', () => {
    const { result } = renderHook(() => useFileMappingForm(files));

    act(() => result.current.applyToAll(seriesRequest, [files[0]]));

    expect(result.current.buildPayload(files)).toEqual([
      {
        file_id: 'f1',
        request_mapping: {
          request_id: 'req-1',
          request_title: 'Show',
          mapping_type: 'series',
          season: 2,
          episode: 1,
        },
      },
    ]);
  });

  it('reverts drafts back to their initial values on reset', () => {
    const { result } = renderHook(() => useFileMappingForm(files));

    act(() => result.current.applyToAll(seriesRequest, files));
    expect(result.current.dirtyFileIds).toHaveLength(3);

    act(() => result.current.reset());
    expect(result.current.dirtyFileIds).toEqual([]);
  });

  it('seeds drafts from mappings that already exist on the files', () => {
    const mapped: ReleaseFile[] = [
      {
        ...files[0],
        request_mapping: {
          request_id: 'req-9',
          request_title: 'Existing',
          mapping_type: 'series',
          season: 3,
          episode: 7,
        },
      },
    ];

    const { result } = renderHook(() => useFileMappingForm(mapped));

    expect(result.current.getDraft('f1')).toMatchObject({
      requestId: 'req-9',
      mappingType: 'series',
      season: 3,
      episode: 7,
    });
    expect(result.current.dirtyFileIds).toEqual([]);
  });

  it('routes each file of a multi-season pack to the request owning its season', () => {
    const { result } = renderHook(() => useFileMappingForm(packFiles, packDefault, packRequests));

    expect(result.current.getDraft('p1')).toMatchObject({ requestId: 'req-s1', season: 1 });
    expect(result.current.getDraft('p2')).toMatchObject({ requestId: 'req-s2', season: 2 });
    expect(result.current.getDraft('p3')).toMatchObject({ requestId: 'req-s3', season: 3, episode: 1 });
  });

  it('spreads a pack across seasons when applying one request to all files', () => {
    const { result } = renderHook(() => useFileMappingForm(packFiles, undefined, packRequests));

    act(() => result.current.applyToAll(packRequests[0], packFiles));

    expect(result.current.getDraft('p2')).toMatchObject({ requestId: 'req-s2', season: 2 });
    expect(result.current.getDraft('p3')).toMatchObject({ requestId: 'req-s3', season: 3 });
  });

  it('counts auto-filled episodes per season instead of across the whole release', () => {
    const unnumbered: ReleaseFile[] = [
      { id: 'u1', name: 'a.mkv', size: 1, path: 'Avatar/Season 1/a.mkv' },
      { id: 'u2', name: 'b.mkv', size: 1, path: 'Avatar/Season 1/b.mkv' },
      { id: 'u3', name: 'c.mkv', size: 1, path: 'Avatar/Season 2/c.mkv' },
    ];

    const { result } = renderHook(() => useFileMappingForm(unnumbered, packDefault, packRequests));

    act(() => result.current.autoFillEpisodes(unnumbered));

    expect(result.current.getDraft('u1')).toMatchObject({ season: 1, episode: 1 });
    expect(result.current.getDraft('u2')).toMatchObject({ season: 1, episode: 2 });
    expect(result.current.getDraft('u3')).toMatchObject({ requestId: 'req-s2', season: 2, episode: 1 });
  });

  it('leaves series files without an episode number out of the payload', () => {
    const unparseable: ReleaseFile[] = [
      { id: 'x1', name: 'behind the scenes.mkv', size: 1, path: 'Avatar/behind the scenes.mkv' },
    ];

    const { result } = renderHook(() => useFileMappingForm(unparseable, packDefault, packRequests));

    expect(result.current.buildPayload(unparseable)).toEqual([]);
  });
});
