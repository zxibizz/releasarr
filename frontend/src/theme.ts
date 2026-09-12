import { Tooltip, createTheme } from '@mantine/core';

const fontStack =
  "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";

export const theme = createTheme({
  primaryColor: 'blue',
  primaryShade: { light: 6, dark: 7 },
  defaultRadius: 'md',
  focusRing: 'auto',
  fontFamily: fontStack,
  fontFamilyMonospace: "'JetBrains Mono', 'Fira Code', 'Source Code Pro', monospace",
  headings: {
    fontFamily: fontStack,
    fontWeight: '700',
    sizes: {
      // Page titles at their desktop size leave no room for anything beside
      // them on a phone, so they scale with the viewport up to that size.
      h1: { fontSize: 'clamp(1.5rem, 1.1rem + 2vw, 2.125rem)' },
      h2: { fontSize: 'clamp(1.3rem, 1rem + 1.5vw, 1.625rem)' },
      h3: { fontSize: 'clamp(1.15rem, 0.95rem + 1vw, 1.375rem)' },
    },
  },
  cursorType: 'pointer',
  // `global.css` already drops CSS animations for this preference; without this
  // Mantine's own JS-driven transitions would keep running anyway.
  respectReducedMotion: true,
  components: {
    // Touch has no hover, so a tap has to be able to open a tooltip.
    Tooltip: Tooltip.extend({
      defaultProps: {
        events: { hover: true, focus: true, touch: true },
      },
    }),
  },
});
