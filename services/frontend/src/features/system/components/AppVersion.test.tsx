import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AppVersion } from '@/features/system/components/AppVersion';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('AppVersion', () => {
  it('shows the version the backend reports', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ version: '1.2.3', database: 'sqlite' });

    renderWithProviders(<AppVersion />);

    expect(await screen.findByText('Releasarr v1.2.3')).toBeInTheDocument();
    expect(apiRequest).toHaveBeenCalledWith('/system', expect.anything());
  });

  it('renders nothing when the version cannot be read', async () => {
    vi.mocked(apiRequest).mockRejectedValue(new Error('offline'));

    renderWithProviders(<AppVersion />);

    await vi.waitFor(() => expect(apiRequest).toHaveBeenCalled());
    expect(screen.queryByText(/Releasarr/)).not.toBeInTheDocument();
  });
});
