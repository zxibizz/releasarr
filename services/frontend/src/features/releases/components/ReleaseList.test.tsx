import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ReleaseList } from '@/features/releases/components/ReleaseList';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { Release, ReleaseRefreshResponse } from '@/types';

const notificationsMock = vi.hoisted(() => ({ show: vi.fn(), hide: vi.fn() }));

vi.mock('@mantine/notifications', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@mantine/notifications')>()),
  notifications: notificationsMock,
}));

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

/** Answers the release list, the request titles it reads, and a refresh call. */
function mockApi(progress: number, refresh?: Partial<ReleaseRefreshResponse>) {
  vi.mocked(apiRequest).mockImplementation((path: string) => {
    if (path === '/requests/1/releases/refresh') {
      return Promise.resolve({
        releases: [release(progress)],
        statuses_updated: 0,
        regrabbed: 0,
        ...refresh,
      }) as never;
    }
    return Promise.resolve(
      path.endsWith('/releases') ? { releases: [release(progress)] } : { requests: [], total: 0 },
    ) as never;
  });
}

const REFRESH_BUTTON = /Check download progress/;

function renderList() {
  return renderWithProviders(
    <ReleaseList requestId="1" onViewFiles={() => {}} onReleasesLoaded={() => {}} />,
  );
}

describe('ReleaseList', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    notificationsMock.show.mockClear();
  });

  it('asks the server to check the releases when refresh is pressed', async () => {
    mockApi(41);
    renderList();

    expect(await screen.findByText('41.0%')).toBeInTheDocument();

    // Reading the list back only ever re-reads what the server already knows:
    // progress lives in the download client and a replaced release surfaces
    // only when its indexer is checked, so refresh asks for the work to be done
    // and the server hands back the result in the response.
    mockApi(41, { releases: [release(88)], statuses_updated: 1 });
    await userEvent.click(screen.getByRole('button', { name: REFRESH_BUTTON }));

    expect(await screen.findByText('88.0%')).toBeInTheDocument();
    expect(vi.mocked(apiRequest)).toHaveBeenCalledWith('/requests/1/releases/refresh', {
      method: 'POST',
    });
    expect(
      vi.mocked(apiRequest).mock.calls.filter(([path]) => path === '/requests/1/releases'),
    ).toHaveLength(1);
  });

  it('says how many releases were re-grabbed', async () => {
    mockApi(41);
    renderList();
    await screen.findByText('41.0%');

    mockApi(41, { regrabbed: 2 });
    await userEvent.click(screen.getByRole('button', { name: REFRESH_BUTTON }));

    expect(notificationsMock.show).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Releases refreshed',
        message: '2 releases were re-grabbed',
      }),
    );
  });

  it('reports a refresh the server refused', async () => {
    mockApi(41);
    renderList();
    await screen.findByText('41.0%');

    vi.mocked(apiRequest).mockImplementation((path: string) =>
      path === '/requests/1/releases/refresh'
        ? (Promise.reject(new Error('qBittorrent is not configured')) as never)
        : (Promise.resolve({ requests: [], total: 0 }) as never),
    );
    await userEvent.click(screen.getByRole('button', { name: REFRESH_BUTTON }));

    expect(notificationsMock.show).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Unable to refresh releases',
        message: 'qBittorrent is not configured',
        color: 'red',
      }),
    );
    // A refresh that could not run leaves the list that was already loaded.
    expect(screen.getByText('41.0%')).toBeInTheDocument();
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
