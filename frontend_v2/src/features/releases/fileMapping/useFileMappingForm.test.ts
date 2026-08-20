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
});
