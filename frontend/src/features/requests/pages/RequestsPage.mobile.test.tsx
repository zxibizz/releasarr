import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { RequestsPage } from '@/features/requests/pages/RequestsPage';
import { apiRequest } from '@/lib/api/client';
import { DESKTOP_WIDTH, MOBILE_WIDTH, renderWithProviders, setViewportWidth } from '@/test/utils';
import type { MediaRequest } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const movie: MediaRequest = {
  id: '1',
  type: 'movie',
  title: 'The Dark Knight',
  year: 2008,
  runtime: 152,
  imdb_id: 'tt0468569',
  poster_url: 'https://example.test/poster.jpg',
  overview: 'Batman raises the stakes in his war on crime.',
  genres: ['Action', 'Crime'],
  status: 'completed',
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: '2026-01-02T00:00:00.000Z',
};

describe('RequestsPage on a phone', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    vi.mocked(apiRequest).mockResolvedValue({ requests: [movie], total: 1 });
    setViewportWidth(MOBILE_WIDTH);
  });

  afterEach(() => {
    setViewportWidth(DESKTOP_WIDTH);
  });

  it('leaves genres and the synopsis off the cards', async () => {
    renderWithProviders(<RequestsPage />);

    expect(await screen.findByText('The Dark Knight')).toBeInTheDocument();
    expect(screen.queryByText('Action')).not.toBeInTheDocument();
    expect(screen.queryByText('Crime')).not.toBeInTheDocument();
    expect(screen.queryByText(/war on crime/i)).not.toBeInTheDocument();
  });

  it('keeps sort behind a toggle so the list starts higher up the screen', async () => {
    renderWithProviders(<RequestsPage />);

    await screen.findByText('The Dark Knight');
    expect(screen.queryByRole('combobox', { name: /sort requests/i })).not.toBeInTheDocument();

    const toggle = screen.getByRole('button', { name: /sort and language/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await userEvent.click(toggle);

    await waitFor(() => expect(toggle).toHaveAttribute('aria-expanded', 'true'));
    expect(await screen.findByRole('combobox', { name: /sort requests/i })).toBeInTheDocument();
  });

  it('drops the headline totals that the result count already shows', async () => {
    renderWithProviders(<RequestsPage />);

    await screen.findByText('The Dark Knight');
    expect(screen.queryByText(/total requests/i)).not.toBeInTheDocument();
    expect(screen.getByText('1 request')).toBeInTheDocument();
  });

  it('still shows genres, the synopsis and the totals on a desktop', async () => {
    setViewportWidth(DESKTOP_WIDTH);

    renderWithProviders(<RequestsPage />);

    expect(await screen.findByText('The Dark Knight')).toBeInTheDocument();
    expect(screen.getByText('Action')).toBeInTheDocument();
    expect(screen.getByText(/war on crime/i)).toBeInTheDocument();

    const totals = screen.getByText(/total requests/i).closest('div');
    expect(totals && within(totals).getByText('1')).toBeInTheDocument();
  });
});
