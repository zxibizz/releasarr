import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { useLogFilters } from '@/features/logs/useLogFilters';
import { renderWithProviders } from '@/test/utils';

function Probe() {
  const { service, task, setService, setTask } = useLogFilters();

  return (
    <div>
      <span data-testid="service">{service}</span>
      <span data-testid="task">{task ?? 'none'}</span>
      <button type="button" onClick={() => setService('scheduler')}>
        scheduler
      </button>
      <button type="button" onClick={() => setService('api')}>
        api
      </button>
      <button type="button" onClick={() => setTask(undefined)}>
        clear task
      </button>
    </div>
  );
}

describe('useLogFilters', () => {
  it('reads the defaults when the URL says nothing', () => {
    renderWithProviders(<Probe />);

    expect(screen.getByTestId('service')).toHaveTextContent('api');
    expect(screen.getByTestId('task')).toHaveTextContent('none');
  });

  it('reads what the URL names', () => {
    renderWithProviders(<Probe />, { route: '/system/logs?service=scheduler&task=export' });

    expect(screen.getByTestId('service')).toHaveTextContent('scheduler');
    expect(screen.getByTestId('task')).toHaveTextContent('export');
  });

  it('ignores a service it does not know', () => {
    renderWithProviders(<Probe />, { route: '/system/logs?service=nonsense' });

    expect(screen.getByTestId('service')).toHaveTextContent('api');
  });

  it('drops the task filter when the process changes', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Probe />, { route: '/system/logs?service=scheduler&task=export' });

    await user.click(screen.getByRole('button', { name: 'api' }));

    // Both changes have to survive: the URL is written once, not twice.
    await waitFor(() => expect(screen.getByTestId('task')).toHaveTextContent('none'));
    expect(screen.getByTestId('service')).toHaveTextContent('api');
  });

  it('leaves the task filter alone when the process does not change', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Probe />, { route: '/system/logs?task=export' });

    await user.click(screen.getByRole('button', { name: 'api' }));

    expect(screen.getByTestId('task')).toHaveTextContent('export');
  });

  it('clears the task filter on its own', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Probe />, { route: '/system/logs?service=scheduler&task=export' });

    await user.click(screen.getByRole('button', { name: 'clear task' }));

    await waitFor(() => expect(screen.getByTestId('task')).toHaveTextContent('none'));
    expect(screen.getByTestId('service')).toHaveTextContent('scheduler');
  });
});
