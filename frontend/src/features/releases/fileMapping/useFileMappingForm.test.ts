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
const ALREADY_AT_TWELVE = [suggest('u1', 'req-s1', 1, 12)];

describe('useFileMappingForm', () => {
  it('starts with empty drafts and no pending changes', () => {
    const { result } = renderHook(() => useFileMappingForm(files));

    expect(result.current.getDraft('f1').requestId).toBe('');
    expect(result.current.dirtyFileIds).toEqual([]);
    expect(result.current.buildPayload(files)).toEqual([]);
  });

  it('applies a series request to every file, leaving the episode to be filled in', () => {
    const { result } = renderHook(() => useFileMappingForm(files));

    act(() => result.current.applyToAll(seriesRequest, files));

    expect(result.current.getDraft('f1')).toMatchObject({
      requestId: 'req-1',
      mappingType: 'series',
      season: 2,
      episode: undefined,
    });
    expect(result.current.dirtyFileIds).toHaveLength(3);
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

  it('puts the proposals back over an edit when asked to', () => {
    const { result } = renderHook(() =>
      useFileMappingForm(packFiles, packRequests, packSuggestions),
    );

    act(() => result.current.selectRequest('p1', packRequests[2]));
    expect(result.current.getDraft('p1')).toMatchObject({ requestId: 'req-s3' });

    act(() => result.current.applySuggestions());

    expect(result.current.getDraft('p1')).toMatchObject({
      requestId: 'req-s1',
      season: 1,
      episode: 1,
    });
  });

  it('spreads a pack across seasons when applying one request to all files', () => {
    const { result } = renderHook(() =>
      useFileMappingForm(packFiles, packRequests, packSuggestions),
    );

    act(() => result.current.applyToAll(packRequests[0], packFiles));

    expect(result.current.getDraft('p2')).toMatchObject({ requestId: 'req-s2', season: 2 });
    expect(result.current.getDraft('p3')).toMatchObject({ requestId: 'req-s3', season: 3 });
  });

  it('numbers episodes per season instead of across the whole release', () => {
    const unnumbered: ReleaseFile[] = [
      { id: 'u1', name: 'a.mkv', size: 1, path: 'Avatar/Season 1/a.mkv' },
      { id: 'u2', name: 'b.mkv', size: 1, path: 'Avatar/Season 1/b.mkv' },
      { id: 'u3', name: 'c.mkv', size: 1, path: 'Avatar/Season 2/c.mkv' },
    ];

    const { result } = renderHook(() => useFileMappingForm(unnumbered, packRequests));

    act(() => result.current.applyToAll(packRequests[0], [unnumbered[0], unnumbered[1]]));
    act(() => result.current.applyToAll(packRequests[1], [unnumbered[2]]));
    act(() => result.current.numberEpisodes(unnumbered));

    expect(result.current.getDraft('u1')).toMatchObject({ season: 1, episode: 1 });
    expect(result.current.getDraft('u2')).toMatchObject({ season: 1, episode: 2 });
    expect(result.current.getDraft('u3')).toMatchObject({
      requestId: 'req-s2',
      season: 2,
      episode: 1,
    });
  });

  it('numbers from the highest episode already set rather than from one', () => {
    const unnumbered: ReleaseFile[] = [
      { id: 'u1', name: 'a.mkv', size: 1, path: 'Avatar/Season 1/a.mkv' },
      { id: 'u2', name: 'b.mkv', size: 1, path: 'Avatar/Season 1/b.mkv' },
    ];

    const { result } = renderHook(() =>
      useFileMappingForm(unnumbered, packRequests, ALREADY_AT_TWELVE),
    );

    act(() => result.current.applyToAll(packRequests[0], unnumbered));
    act(() => result.current.numberEpisodes(unnumbered));

    expect(result.current.getDraft('u1')).toMatchObject({ episode: 12 });
    expect(result.current.getDraft('u2')).toMatchObject({ episode: 13 });
  });

  it('leaves series files without an episode number out of the payload', () => {
    const unmatched: ReleaseFile[] = [
      { id: 'x1', name: 'behind the scenes.mkv', size: 1, path: 'Avatar/behind the scenes.mkv' },
    ];

    const { result } = renderHook(() => useFileMappingForm(unmatched, packRequests));

    act(() => result.current.applyToAll(packRequests[0], unmatched));

    expect(result.current.getDraft('x1')).toMatchObject({ season: 1, episode: undefined });
    expect(result.current.buildPayload(unmatched)).toEqual([]);
  });
});
