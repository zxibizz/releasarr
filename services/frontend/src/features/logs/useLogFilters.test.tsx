import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { useLogFilters } from '@/features/logs/useLogFilters';
import { renderWithProviders } from '@/test/utils';

function Probe() {
  const { service, component, setService, setComponent } = useLogFilters();

  return (
    <div>
      <span data-testid="service">{service ?? 'all'}</span>
      <span data-testid="component">{component ?? 'all'}</span>
      <button type="button" onClick={() => setService('scheduler')}>
        scheduler
      </button>
      <button type="button" onClick={() => setService(undefined)}>
        all services
      </button>
      <button type="button" onClick={() => setComponent('usecase.export')}>
        export
      </button>
      <button type="button" onClick={() => setComponent(undefined)}>
        clear component
      </button>
    </div>
  );
}

describe('useLogFilters', () => {
  it('reads the defaults when the URL says nothing', () => {
    renderWithProviders(<Probe />);

    expect(screen.getByTestId('service')).toHaveTextContent('all');
    expect(screen.getByTestId('component')).toHaveTextContent('all');
  });

  it('reads what the URL names', () => {
    renderWithProviders(<Probe />, {
      route: '/system/logs?service=scheduler&component=usecase.export',
    });

    expect(screen.getByTestId('service')).toHaveTextContent('scheduler');
    expect(screen.getByTestId('component')).toHaveTextContent('usecase.export');
  });

  it('ignores values it does not know', () => {
    renderWithProviders(<Probe />, { route: '/system/logs?service=nonsense&component=bogus' });

    expect(screen.getByTestId('service')).toHaveTextContent('all');
    expect(screen.getByTestId('component')).toHaveTextContent('all');
  });

  it('writes a service to the URL', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Probe />);

    await user.click(screen.getByRole('button', { name: 'scheduler' }));

    await waitFor(() => expect(screen.getByTestId('service')).toHaveTextContent('scheduler'));
  });

  it('clears a filter without disturbing the other', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Probe />, {
      route: '/system/logs?service=scheduler&component=usecase.export',
    });

    await user.click(screen.getByRole('button', { name: 'all services' }));

    await waitFor(() => expect(screen.getByTestId('service')).toHaveTextContent('all'));
    expect(screen.getByTestId('component')).toHaveTextContent('usecase.export');
  });

  it('sets and clears a component independently', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Probe />);

    await user.click(screen.getByRole('button', { name: 'export' }));
    await waitFor(() =>
      expect(screen.getByTestId('component')).toHaveTextContent('usecase.export'),
    );

    await user.click(screen.getByRole('button', { name: 'clear component' }));
    await waitFor(() => expect(screen.getByTestId('component')).toHaveTextContent('all'));
  });
});
