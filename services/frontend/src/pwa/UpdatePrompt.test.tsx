import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { UpdatePrompt } from '@/pwa/UpdatePrompt';
import { renderWithProviders } from '@/test/utils';

const notificationsMock = vi.hoisted(() => ({ show: vi.fn(), hide: vi.fn() }));

const pwaMock = vi.hoisted(() => ({
  needRefresh: false,
  updateServiceWorker: vi.fn(),
}));

vi.mock('@mantine/notifications', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@mantine/notifications')>()),
  notifications: notificationsMock,
}));

vi.mock('virtual:pwa-register/react', () => ({
  useRegisterSW: () => ({
    offlineReady: [false, () => {}],
    needRefresh: [pwaMock.needRefresh, () => {}],
    updateServiceWorker: pwaMock.updateServiceWorker,
  }),
}));

describe('UpdatePrompt', () => {
  beforeEach(() => {
    notificationsMock.show.mockClear();
    pwaMock.updateServiceWorker.mockClear();
    pwaMock.needRefresh = false;
  });

  it('stays quiet while the running build is the current one', () => {
    renderWithProviders(<UpdatePrompt />);

    expect(notificationsMock.show).not.toHaveBeenCalled();
  });

  it('announces a build that is waiting to take over', () => {
    pwaMock.needRefresh = true;

    renderWithProviders(<UpdatePrompt />);

    expect(notificationsMock.show).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'releasarr-update', autoClose: false }),
    );
  });

  it('reloads onto the waiting build when the visitor accepts', async () => {
    pwaMock.needRefresh = true;
    renderWithProviders(<UpdatePrompt />);

    // The notification store has no slot for an action, so the button is part
    // of the notification body — rendering that body is how it gets pressed.
    const [{ message }] = notificationsMock.show.mock.calls.at(-1) as [{ message: ReactElement }];
    renderWithProviders(message);

    await userEvent.click(screen.getByRole('button', { name: 'Reload' }));

    expect(pwaMock.updateServiceWorker).toHaveBeenCalledWith(true);
  });
});
