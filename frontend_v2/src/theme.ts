import { createTheme } from '@mantine/core';

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
  },
  cursorType: 'pointer',
});
