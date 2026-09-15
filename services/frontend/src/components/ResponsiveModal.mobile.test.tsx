import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { ResponsiveModal } from '@/components/ResponsiveModal';
import { DESKTOP_WIDTH, MOBILE_WIDTH, renderWithProviders, setViewportWidth } from '@/test/utils';

function renderModal() {
  renderWithProviders(
    <ResponsiveModal opened onClose={() => {}} title="Manage seasons">
      <p>Seasons</p>
    </ResponsiveModal>,
  );
}

/**
 * The shell header claims the top inset for itself, but a dialog renders into a
 * portal, out of its reach — and in a standalone iOS window the inset is the
 * whole reason a phone's dialogs are not covered by the status bar.
 */
describe('ResponsiveModal under the iOS status bar', () => {
  afterEach(() => {
    setViewportWidth(DESKTOP_WIDTH);
  });

  it('claims the inset inside the full-screen panel a phone gets', async () => {
    setViewportWidth(MOBILE_WIDTH);

    renderModal();

    // Mantine puts `role="dialog"` on the panel, not on the wrapper.
    const panel = await screen.findByRole('dialog');
    expect(panel).toHaveAttribute('data-full-screen');
    expect(panel).toHaveClass('safe-area-top');
  });

  it('leaves a desktop panel unpadded, and moves its float instead', async () => {
    setViewportWidth(DESKTOP_WIDTH);

    renderModal();

    const panel = await screen.findByRole('dialog');
    // Padding here would stack on top of the float and open a gap the height of
    // the notch in a dialog that is nowhere near it.
    expect(panel).not.toHaveClass('safe-area-top');

    // The float is the mechanism that does clear the inset. Mantine writes it to
    // `--modal-y-offset` as an inline style, out of a stylesheet's reach, which
    // is why it comes from `yOffset` in `theme.ts`.
    const root = panel.parentElement?.parentElement;
    expect(root?.style.getPropertyValue('--modal-y-offset')).toContain(
      'max(5dvh, env(safe-area-inset-top))',
    );
  });
});
