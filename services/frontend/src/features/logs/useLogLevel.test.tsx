import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { useLogLevel } from '@/features/logs/useLogLevel';
import { renderWithProviders } from '@/test/utils';

const STORAGE_KEY = 'releasarr.logLevel';

function Probe() {
  const { level, setLevel } = useLogLevel();

  return (
    <div>
      <span data-testid="level">{level ?? 'all'}</span>
      <button type="button" onClick={() => setLevel('warning')}>
        warning
      </button>
      <button type="button" onClick={() => setLevel('error')}>
        error
      </button>
      <button type="button" onClick={() => setLevel(undefined)}>
        all
      </button>
    </div>
  );
}

afterEach(() => {
  window.localStorage.clear();
});

describe('useLogLevel', () => {
  it('shows every level when nothing is stored', () => {
    renderWithProviders(<Probe />);

    expect(screen.getByTestId('level')).toHaveTextContent('all');
  });

  it('opens at the level the last visit chose', () => {
    window.localStorage.setItem(STORAGE_KEY, 'warning');

    renderWithProviders(<Probe />);

    expect(screen.getByTestId('level')).toHaveTextContent('warning');
  });

  it('remembers a choice for the next visit', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Probe />);

    await user.click(screen.getByRole('button', { name: 'error' }));

    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('error');
    expect(screen.getByTestId('level')).toHaveTextContent('error');
  });

  it('forgets the choice once every level is asked for again', async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(STORAGE_KEY, 'error');
    renderWithProviders(<Probe />);

    await user.click(screen.getByRole('button', { name: 'all' }));

    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(screen.getByTestId('level')).toHaveTextContent('all');
  });

  it('ignores a stored value it does not recognise', () => {
    window.localStorage.setItem(STORAGE_KEY, 'verbose');

    renderWithProviders(<Probe />);

    expect(screen.getByTestId('level')).toHaveTextContent('all');
  });
});
