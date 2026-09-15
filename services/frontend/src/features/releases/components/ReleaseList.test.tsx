import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ReleaseList } from '@/features/releases/components/ReleaseList';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { Release } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const release = (progress: number): Release => ({
  id: 'rel-1',
  name: 'Severance.S02E01.2160p.WEB-DL-FLUX',
  hash: 'abc123',
  size: 12_400_000_000,
  files: [],
  status: 'downloading',
  progress,
  download_speed: 4_200_000,
  upload_speed: 0,
  seeders: 40,
  leechers: 2,
  ratio: 0.1,
  added_date: '2026-09-10T00:00:00.000Z',
  request_ids: ['1'],
  torrent_source: 'Indexer A',
  quality: '2160p',
  warnings: [],
});

/** Answers both the release list and the requests list it reads titles from. */
function mockApi(progress: number) {
  vi.mocked(apiRequest).mockImplementation(
    (path: string) =>
      Promise.resolve(
        path.endsWith('/releases') ? { releases: [release(progress)] } : { requests: [], total: 0 },
      ) as never,
  );
}

function renderList() {
  return renderWithProviders(
    <ReleaseList requestId="1" onViewFiles={() => {}} onReleasesLoaded={() => {}} />,
  );
}

describe('ReleaseList', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('refetches the releases when refresh is pressed', async () => {
    mockApi(41);
    renderList();

    expect(await screen.findByText('41.0%')).toBeInTheDocument();

    // Download progress is only as fresh as the last fetch, so the button has
    // to reach the server rather than re-render the cached list.
    mockApi(88);
    await userEvent.click(screen.getByRole('button', { name: 'Refresh' }));

    expect(await screen.findByText('88.0%')).toBeInTheDocument();
    expect(
      vi.mocked(apiRequest).mock.calls.filter(([path]) => path === '/requests/1/releases'),
    ).toHaveLength(2);
  });

  it('shows a warning banner when a release has a mapping overlap', async () => {
    vi.mocked(apiRequest).mockImplementation(
      (path: string) =>
        Promise.resolve(
          path.endsWith('/releases')
            ? {
                releases: [
                  {
                    ...release(41),
                    warnings: [
                      {
                        code: 'mapping_overlap',
                        file_ids: ['file-1'],
                        related_release_ids: ['rel-2'],
                        details: null,
                      },
                    ],
                  },
                ],
              }
            : { requests: [], total: 0 },
        ) as never,
    );

    renderList();

    expect(await screen.findByText('Overlapping releases')).toBeInTheDocument();
  });

  it('shows no warning banner when releases do not overlap', async () => {
    mockApi(41);
    renderList();

    await screen.findByText('41.0%');

    expect(screen.queryByText('Overlapping releases')).not.toBeInTheDocument();
  });

  it('shows an indexer-unavailable badge on the release card after a failed regrab', async () => {
    vi.mocked(apiRequest).mockImplementation(
      (path: string) =>
        Promise.resolve(
          path.endsWith('/releases')
            ? {
                releases: [
                  {
                    ...release(41),
                    warnings: [
                      {
                        code: 'regrab_indexer_unavailable',
                        file_ids: [],
                        related_release_ids: [],
                        details: { reason: 'indexer banned' },
                      },
                    ],
                  },
                ],
              }
            : { requests: [], total: 0 },
        ) as never,
    );

    renderList();

    expect(await screen.findByText('Indexer unavailable')).toBeInTheDocument();
  });
});
