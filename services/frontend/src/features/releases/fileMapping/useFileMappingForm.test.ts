import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useFileMappingForm } from '@/features/releases/fileMapping/useFileMappingForm';
import type { MediaRequest, ReleaseFile, ReleaseFileMappingSuggestion } from '@/types';

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

const movieRequest: MediaRequest = {
  id: 'req-m',
  type: 'movie',
  title: 'Dune: Part Two',
  year: 2024,
  runtime: 166,
  imdb_id: 'tt15239678',
  poster_url: 'https://example.test/dune.jpg',
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
  {
    id: 'p3',
    name: '01 - The Awakening.mkv',
    size: 1,
    path: 'Avatar/Season 3/01 - The Awakening.mkv',
  },
];

const packRequests = [
  seasonRequest('req-s1', 1),
  seasonRequest('req-s2', 2),
  seasonRequest('req-s3', 3),
];

const suggest = (
  fileId: string,
  requestId: string,
  season: number,
  episode: number,
): ReleaseFileMappingSuggestion => ({
  file_id: fileId,
  request_mapping: {
    request_id: requestId,
    request_title: `Avatar - Season ${season}`,
    mapping_type: 'series',
    season,
    episode,
  },
});

const packSuggestions: ReleaseFileMappingSuggestion[] = [
  suggest('p1', 'req-s1', 1, 1),
  suggest('p2', 'req-s2', 2, 1),
  suggest('p3', 'req-s3', 3, 1),
];

const NO_SUGGESTIONS: ReleaseFileMappingSuggestion[] = [];

describe('useFileMappingForm', () => {
  it('starts with empty drafts and no pending changes', () => {
    const { result } = renderHook(() => useFileMappingForm(files));

    expect(result.current.getDraft('f1').requestId).toBe('');
    expect(result.current.dirtyFileIds).toEqual([]);
    expect(result.current.buildPayload(files)).toEqual([]);
  });

  it('maps the whole release onto its own request, numbering what it cannot place', () => {
    const { result } = renderHook(() => useFileMappingForm(files, packRequests));

    act(() => result.current.automap(seriesRequest, [files[0], files[1]]));

    // The request owns a season but no series entry for it, so it maps itself;
    // the files are numbered in name order from one.
    expect(result.current.getDraft('f1')).toMatchObject({
      requestId: 'req-1',
      requestTitle: 'Show',
      mappingType: 'series',
      season: 2,
      episode: 1,
    });
    expect(result.current.getDraft('f2')).toMatchObject({
      requestId: 'req-1',
      mappingType: 'series',
      season: 2,
      episode: 2,
    });
    // Not one of the files it was handed, so it is left alone.
    expect(result.current.getDraft('f3').requestId).toBe('');

    expect(result.current.buildPayload([files[0], files[1]])).toEqual([
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
      {
        file_id: 'f2',
        request_mapping: {
          request_id: 'req-1',
          request_title: 'Show',
          mapping_type: 'series',
          season: 2,
          episode: 2,
        },
      },
    ]);
  });

  it('replaces the stored mappings rather than building on them', () => {
    const stored: ReleaseFile[] = [
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
      {
        ...files[2],
        request_mapping: {
          request_id: 'req-9',
          request_title: 'Existing',
          mapping_type: 'movie',
        },
      },
    ];

    const { result } = renderHook(() => useFileMappingForm(stored, packRequests));

    expect(result.current.getDraft('f1')).toMatchObject({ requestId: 'req-9', episode: 7 });

    act(() => result.current.automap(seriesRequest, [stored[0]]));

    // The stored season 3 episode 7 is gone, not carried over.
    expect(result.current.getDraft('f1')).toMatchObject({
      requestId: 'req-1',
      season: 2,
      episode: 1,
    });

    // And saving says so: the file automapping did not speak for is cleared
    // rather than left on the mapping it used to have.
    expect(result.current.buildPayload(stored)).toEqual([
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
      { file_id: 'f3', request_mapping: null },
    ]);
  });

  it('numbers files on after the episodes the automapper placed itself', () => {
    const mixed: ReleaseFile[] = [
      { id: 'a', name: 'Avatar.S01E01.mkv', size: 1, path: 'Avatar/Avatar.S01E01.mkv' },
      { id: 'b', name: 'Second.mkv', size: 1, path: 'Avatar/Second.mkv' },
      { id: 'c', name: 'Third.mkv', size: 1, path: 'Avatar/Third.mkv' },
    ];

    const { result } = renderHook(() =>
      useFileMappingForm(mixed, packRequests, [suggest('a', 'req-s1', 1, 1)]),
    );

    act(() => result.current.automap(packRequests[0], mixed));

    // The proposal keeps its episode; numbering carries on from it instead of
    // starting again at one and clashing with it.
    expect(result.current.getDraft('a')).toMatchObject({
      requestId: 'req-s1',
      season: 1,
      episode: 1,
    });
    expect(result.current.getDraft('b')).toMatchObject({
      requestId: 'req-s1',
      season: 1,
      episode: 2,
    });
    expect(result.current.getDraft('c')).toMatchObject({
      requestId: 'req-s1',
      season: 1,
      episode: 3,
    });
  });

  it('maps every listed file to a movie request', () => {
    const { result } = renderHook(() => useFileMappingForm(files, packRequests));

    act(() => result.current.automap(movieRequest, [files[0], files[1]]));

    expect(result.current.getDraft('f1')).toMatchObject({
      requestId: 'req-m',
      requestTitle: 'Dune: Part Two',
      mappingType: 'movie',
    });
    expect(result.current.buildPayload([files[0], files[1]])).toEqual([
      {
        file_id: 'f1',
        request_mapping: {
          request_id: 'req-m',
          request_title: 'Dune: Part Two',
          mapping_type: 'movie',
        },
      },
      {
        file_id: 'f2',
        request_mapping: {
          request_id: 'req-m',
          request_title: 'Dune: Part Two',
          mapping_type: 'movie',
        },
      },
    ]);
  });

  it('leaves the stored mappings alone when there is no request to map to', () => {
    const stored: ReleaseFile[] = [
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

    const { result } = renderHook(() => useFileMappingForm(stored, packRequests));

    act(() => result.current.automap(undefined, stored));

    expect(result.current.getDraft('f1').requestId).toBe('');
    expect(result.current.buildPayload(stored)).toEqual([{ file_id: 'f1', request_mapping: null }]);
  });

  it('serialises series mappings into the API payload shape', () => {
    const { result } = renderHook(() =>
      useFileMappingForm(packFiles, packRequests, [suggest('p1', 'req-s1', 1, 4)]),
    );

    expect(result.current.buildPayload(packFiles)).toEqual([
      {
        file_id: 'p1',
        request_mapping: {
          request_id: 'req-s1',
          request_title: 'Avatar - Season 1',
          mapping_type: 'series',
          season: 1,
          episode: 4,
        },
      },
    ]);
  });

  it('reverts drafts back to their initial values on reset', () => {
    const { result } = renderHook(() => useFileMappingForm(files, packRequests));

    act(() => result.current.automap(seriesRequest, [files[0], files[1]]));
    expect(result.current.dirtyFileIds).toHaveLength(2);

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

  it("reports the server's proposals as changes nobody has agreed to yet", () => {
    const { result } = renderHook(() =>
      useFileMappingForm(packFiles, packRequests, packSuggestions),
    );

    expect(result.current.getDraft('p1')).toMatchObject({ requestId: 'req-s1', season: 1 });
    expect(result.current.getDraft('p3')).toMatchObject({
      requestId: 'req-s3',
      season: 3,
      episode: 1,
    });
    expect(result.current.dirtyFileIds).toHaveLength(3);
  });

  it('folds in proposals that arrive after the form has opened', () => {
    const { result, rerender } = renderHook(
      ({ suggestions }: { suggestions: ReleaseFileMappingSuggestion[] }) =>
        useFileMappingForm(packFiles, packRequests, suggestions),
      { initialProps: { suggestions: NO_SUGGESTIONS } },
    );

    expect(result.current.getDraft('p1').requestId).toBe('');

    rerender({ suggestions: packSuggestions });

    expect(result.current.getDraft('p1')).toMatchObject({ requestId: 'req-s1', season: 1 });
  });

  it('leaves a choice made while the proposals were in flight alone', () => {
    const { result, rerender } = renderHook(
      ({ suggestions }: { suggestions: ReleaseFileMappingSuggestion[] }) =>
        useFileMappingForm(packFiles, packRequests, suggestions),
      { initialProps: { suggestions: NO_SUGGESTIONS } },
    );

    act(() => result.current.selectRequest('p1', packRequests[2]));
    rerender({ suggestions: packSuggestions });

    expect(result.current.getDraft('p1')).toMatchObject({ requestId: 'req-s3' });
    expect(result.current.getDraft('p2')).toMatchObject({ requestId: 'req-s2', season: 2 });
  });

  it('clears a mapping when its row is emptied', () => {
    const stored: ReleaseFile[] = [
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

    const { result } = renderHook(() => useFileMappingForm(stored));

    act(() => result.current.selectRequest('f1', null));

    // An emptied row says `null` rather than dropping out of the payload: the
    // stored mapping has to be cleared, not left standing.
    expect(result.current.buildPayload(stored)).toEqual([{ file_id: 'f1', request_mapping: null }]);
    expect(result.current.buildPayload([files[1]])).toEqual([]);
  });

  it('leaves a series choice without an episode number out of the payload', () => {
    const { result } = renderHook(() => useFileMappingForm(files, packRequests));

    act(() => result.current.selectRequest('f1', packRequests[0]));

    expect(result.current.getDraft('f1')).toMatchObject({ season: 1, episode: undefined });
    expect(result.current.buildPayload(files)).toEqual([]);
  });
});
