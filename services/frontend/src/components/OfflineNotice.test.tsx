import { act } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { OfflineNotice } from '@/components/OfflineNotice';
import { renderWithProviders, setOnlineStatus } from '@/test/utils';

const notificationsMock = vi.hoisted(() => ({ show: vi.fn(), hide: vi.fn() }));

vi.mock('@mantine/notifications', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@mantine/notifications')>()),
  notifications: notificationsMock,
}));

describe('OfflineNotice', () => {
  beforeEach(() => {
    notificationsMock.show.mockClear();
    notificationsMock.hide.mockClear();
    setOnlineStatus(true);
  });

  afterEach(() => setOnlineStatus(true));

  it('says nothing while the connection is up', () => {
    renderWithProviders(<OfflineNotice />);

    expect(notificationsMock.show).not.toHaveBeenCalled();
  });

  it('explains a dropped connection in a notice that cannot be dismissed', () => {
    setOnlineStatus(false);

    renderWithProviders(<OfflineNotice />);

    expect(notificationsMock.show).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'releasarr-offline',
        title: 'Cannot reach Releasarr',
        autoClose: false,
        allowClose: false,
      }),
    );
  });

  it('takes the notice back down when the connection returns', () => {
    setOnlineStatus(false);
    renderWithProviders(<OfflineNotice />);

    act(() => setOnlineStatus(true));

    expect(notificationsMock.hide).toHaveBeenCalledWith('releasarr-offline');
  });
});
