import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ReleaseSearch } from '@/features/releases/components/ReleaseSearch';
import { apiRequest } from '@/lib/api/client';
import { DESKTOP_WIDTH, MOBILE_WIDTH, renderWithProviders, setViewportWidth } from '@/test/utils';
import type { ReleaseSearchResult } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

/** Long enough that a phone-width field can only ever show part of it. */
const LONG_NAME = 'Severance.S02E01.Hello.Ms.Cobel.2160p.ATVP.WEB-DL.DDP5.1.Atmos.HDR.H265-FLUX';

const candidate: ReleaseSearchResult = {
  release_id: 'r1',
  release_name: LONG_NAME,
  size: '12.4 GB',
  seeders: 40,
  leechers: 2,
  quality: '2160p',
  source: 'Indexer A',
  publish_date: '2026-09-10T00:00:00.000Z',
};

const withoutQuality: ReleaseSearchResult = {
  release_id: 'r2',
  release_name: 'Severance.S02E01.WEBRip-GROUP',
  size: '2.1 GB',
  quality: null,
  source: 'Indexer B',
  publish_date: '2026-09-11T00:00:00.000Z',
};

const FIELD_LABEL = 'Search releases for Severance';

function renderSearch() {
  return renderWithProviders(
    <ReleaseSearch
      requestId="1"
      requestTitle="Severance"
      prefillQuery="Severance S02E01"
      onDownloadQueued={() => {}}
    />,
  );
}

async function runSearch() {
  await userEvent.click(screen.getByRole('button', { name: 'Search' }));
  return screen.findByText(LONG_NAME);
}

describe('ReleaseSearch on a phone', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    vi.mocked(apiRequest).mockResolvedValue({
      results: [candidate, withoutQuality],
      query: 'Severance S02E01',
      total_results: 2,
    });
    setViewportWidth(MOBILE_WIDTH);
  });

  afterEach(() => {
    setViewportWidth(DESKTOP_WIDTH);
  });

  it('lets a long query wrap instead of hiding it in one line', () => {
    renderSearch();

    expect(screen.getByLabelText(FIELD_LABEL).tagName).toBe('TEXTAREA');
  });

  it('sends a wrapped query as a single line', async () => {
    renderSearch();

    const field = screen.getByLabelText(FIELD_LABEL);
    await userEvent.clear(field);
    await userEvent.type(field, 'Severance{Enter}S02E01');
    await runSearch();

    expect(apiRequest).toHaveBeenCalledWith(
      '/releases/search',
      expect.objectContaining({ query: { q: 'Severance S02E01', request_id: '1' } }),
    );
  });

  it('keeps the sort and source controls behind a toggle', async () => {
    renderSearch();

    await runSearch();
    expect(screen.queryByRole('combobox', { name: 'Sort by' })).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: 'Source' })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Filters' }));

    expect(await screen.findByRole('combobox', { name: 'Sort by' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Source' })).toBeInTheDocument();
  });

  it('says on the toggle when a hidden filter is narrowing the results', async () => {
    renderSearch();

    await runSearch();
    await userEvent.click(screen.getByRole('button', { name: 'Filters' }));
    await userEvent.click(screen.getByRole('combobox', { name: 'Source' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Indexer A' }));

    expect(screen.getByRole('button', { name: 'Filters (active)' })).toBeInTheDocument();
  });

  it('shows the whole release name, tail included', async () => {
    renderSearch();

    const name = await runSearch();
    expect(name).not.toHaveAttribute('data-line-clamp');
  });

  it('leaves out the quality badge when the indexer reported none', async () => {
    renderSearch();

    await runSearch();
    expect(screen.getByText('2160p')).toBeInTheDocument();
    expect(screen.queryByText('Unknown')).not.toBeInTheDocument();
  });

  it('keeps a one-line field and open filters on a desktop', async () => {
    setViewportWidth(DESKTOP_WIDTH);

    renderSearch();
    expect(screen.getByLabelText(FIELD_LABEL).tagName).toBe('INPUT');

    await runSearch();
    expect(await screen.findByRole('combobox', { name: 'Sort by' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Filters' })).not.toBeInTheDocument();
  });
});
