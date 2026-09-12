import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';

import '@/lib/i18n';
import { theme } from '@/theme';

/** Roughly an iPhone 14 in CSS pixels. */
export const MOBILE_WIDTH = 390;
export const DESKTOP_WIDTH = 1280;

/**
 * Answers `max-width` media queries as if the viewport were `width` wide, so the
 * phone and desktop branches of a component can both be rendered under jsdom,
 * which has no layout of its own.
 *
 * Reduced motion is reported as preferred, which is true of jsdom in the sense
 * that matters: it runs no animation frames to finish a transition with, so
 * without this, components that mount their content on `transitionend` would
 * never reveal it.
 */
export function setViewportWidth(width: number) {
  window.matchMedia = ((query: string) => {
    const maxWidthEm = /\(max-width:\s*([\d.]+)em\)/.exec(query);

    const matches = query.includes('prefers-reduced-motion')
      ? true
      : maxWidthEm
        ? width <= Number.parseFloat(maxWidthEm[1]) * 16
        : false;

    return {
      matches,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    };
  }) as unknown as typeof window.matchMedia;
}

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

export function renderWithProviders(
  ui: ReactElement,
  { route = '/', ...options }: RenderOptions & { route?: string } = {},
) {
  const queryClient = createTestQueryClient();

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <MantineProvider theme={theme} forceColorScheme="dark" env="test">
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );

  return { queryClient, ...render(ui, { wrapper: Wrapper, ...options }) };
}
