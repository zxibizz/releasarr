import { extendTheme, type ThemeConfig } from "@chakra-ui/react";

const config: ThemeConfig = {
  initialColorMode: "dark",
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,
  fonts: {
    heading: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    body: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', 'Source Code Pro', monospace",
  },
  semanticTokens: {
    colors: {
      "bg.canvas": "#0b1220",
      "bg.surface": "rgba(30, 41, 59, 0.82)",
      "bg.subtle": "rgba(71, 85, 105, 0.35)",
      "border.muted": "rgba(148, 163, 184, 0.12)",
      "text.subtle": "#94a3b8",
      "text.muted": "#64748b",
    },
  },
  styles: {
    global: {
      "html, body, #root": {
        height: "100%",
      },
      body: {
        bgGradient: "linear(135deg, #0f172a 0%, #1e293b 100%)",
        color: "gray.100",
        minHeight: "100vh",
        lineHeight: "1.6",
        fontFamily: "body",
        WebkitFontSmoothing: "antialiased",
        MozOsxFontSmoothing: "grayscale",
      },
      code: {
        fontFamily: "mono",
        background: "rgba(148, 163, 184, 0.1)",
        paddingInline: "0.25rem",
        paddingBlock: "0.125rem",
        borderRadius: "0.375rem",
        fontSize: "0.875em",
      },
      "::-webkit-scrollbar": {
        width: "8px",
      },
      "::-webkit-scrollbar-track": {
        background: "#1e293b",
      },
      "::-webkit-scrollbar-thumb": {
        background: "linear-gradient(180deg, #475569, #64748b)",
        borderRadius: "999px",
      },
      "::-webkit-scrollbar-thumb:hover": {
        background: "linear-gradient(180deg, #64748b, #94a3b8)",
      },
    },
  },
});

export default theme;
