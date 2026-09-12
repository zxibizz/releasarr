import { useMediaQuery } from '@mantine/hooks';

/**
 * Mantine's `sm` breakpoint. Kept in sync with the `47.99em` queries in
 * `styles/global.css` so the CSS and JS branches switch at the same width.
 */
export const MOBILE_BREAKPOINT = '(max-width: 47.99em)';

/**
 * True on phone-sized viewports. Defaults to `false` while the query resolves so
 * the wider layout renders first and never flashes a narrow one on desktop.
 */
export function useIsMobile(): boolean {
  return useMediaQuery(MOBILE_BREAKPOINT, false) ?? false;
}
