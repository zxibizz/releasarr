import { extendTheme, type ThemeConfig } from '@chakra-ui/react';

const config: ThemeConfig = {
  initialColorMode: 'dark',
  useSystemColorMode: false,
};

const focusRingShadow = '0 0 0 3px rgba(56, 189, 248, 0.65)';

const theme = extendTheme({
  config,
  fonts: {
    heading: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    body: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', 'Source Code Pro', monospace",
  },
  semanticTokens: {
    colors: {
      'bg.canvas': '#0b1220',
      'bg.surface': 'rgba(30, 41, 59, 0.9)',
      'bg.subtle': 'rgba(51, 65, 85, 0.6)',
      'border.muted': 'rgba(148, 163, 184, 0.22)',
      'text.default': '#e2e8f0',
      'text.subtle': '#c7d2fe',
      'text.muted': '#94a3b8',
      'focus.ring': '#38bdf8',
      'focus.border': 'rgba(56, 189, 248, 0.75)',
      'status.pending.bg': 'rgba(250, 204, 21, 0.18)',
      'status.pending.fg': '#FACC15',
      'status.pending.border': 'rgba(250, 204, 21, 0.4)',
      'status.searching.bg': 'rgba(192, 132, 252, 0.18)',
      'status.searching.fg': '#C084FC',
      'status.searching.border': 'rgba(192, 132, 252, 0.4)',
      'status.downloading.bg': 'rgba(96, 165, 250, 0.18)',
      'status.downloading.fg': '#60A5FA',
      'status.downloading.border': 'rgba(96, 165, 250, 0.4)',
      'status.completed.bg': 'rgba(52, 211, 153, 0.18)',
      'status.completed.fg': '#34D399',
      'status.completed.border': 'rgba(52, 211, 153, 0.4)',
      'status.failed.bg': 'rgba(248, 113, 113, 0.18)',
      'status.failed.fg': '#F87171',
      'status.failed.border': 'rgba(248, 113, 113, 0.4)',
      'status.seeding.bg': 'rgba(34, 211, 238, 0.18)',
      'status.seeding.fg': '#22D3EE',
      'status.seeding.border': 'rgba(34, 211, 238, 0.4)',
      'status.info.bg': 'rgba(96, 165, 250, 0.18)',
      'status.info.fg': '#60A5FA',
      'status.info.border': 'rgba(96, 165, 250, 0.4)',
      'status.warning.bg': 'rgba(251, 191, 36, 0.18)',
      'status.warning.fg': '#FBBF24',
      'status.warning.border': 'rgba(251, 191, 36, 0.4)',
      'status.error.bg': 'rgba(248, 113, 113, 0.18)',
      'status.error.fg': '#F87171',
      'status.error.border': 'rgba(248, 113, 113, 0.4)',
    },
  },
  shadows: {
    outline: focusRingShadow,
    focusRing: focusRingShadow,
  },
  components: {
    Button: {
      baseStyle: {
        _focusVisible: {
          boxShadow: 'focusRing',
          outline: 'none',
        },
      },
    },
    IconButton: {
      baseStyle: {
        _focusVisible: {
          boxShadow: 'focusRing',
          outline: 'none',
        },
      },
    },
    Input: {
      baseStyle: {
        field: {
          _focusVisible: {
            borderColor: 'focus.ring',
            boxShadow: '0 0 0 1px var(--chakra-colors-focus-ring)',
          },
        },
      },
    },
    Select: {
      baseStyle: {
        field: {
          _focusVisible: {
            borderColor: 'focus.ring',
            boxShadow: '0 0 0 1px var(--chakra-colors-focus-ring)',
          },
        },
      },
    },
    Link: {
      baseStyle: {
        _focusVisible: {
          boxShadow: 'focusRing',
          outline: 'none',
        },
      },
    },
    Checkbox: {
      baseStyle: {
        control: {
          _focusVisible: {
            boxShadow: 'focusRing',
          },
        },
      },
    },
  },
  styles: {
    global: {
      'html, body, #root': {
        height: '100%',
      },
      body: {
        bgGradient: 'linear(135deg, #0f172a 0%, #1e293b 100%)',
        color: 'text.default',
        minHeight: '100vh',
        lineHeight: '1.6',
        fontFamily: 'body',
        WebkitFontSmoothing: 'antialiased',
        MozOsxFontSmoothing: 'grayscale',
      },
      '*:focus:not(:focus-visible)': {
        boxShadow: 'none !important',
      },
      '*:focus-visible': {
        outline: 'none',
        boxShadow: 'focusRing !important',
      },
      code: {
        fontFamily: 'mono',
        background: 'rgba(148, 163, 184, 0.1)',
        paddingInline: '0.25rem',
        paddingBlock: '0.125rem',
        borderRadius: '0.375rem',
        fontSize: '0.875em',
      },
      '::-webkit-scrollbar': {
        width: '8px',
      },
      '::-webkit-scrollbar-track': {
        background: '#1e293b',
      },
      '::-webkit-scrollbar-thumb': {
        background: 'linear-gradient(180deg, #475569, #64748b)',
        borderRadius: '999px',
      },
      '::-webkit-scrollbar-thumb:hover': {
        background: 'linear-gradient(180deg, #64748b, #94a3b8)',
      },
    },
  },
});

export default theme;
