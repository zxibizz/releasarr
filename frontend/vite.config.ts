import path from 'node:path';
import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react-swc';
import { defineConfig } from 'vitest/config';

const rootDir = path.dirname(fileURLToPath(import.meta.url));

/*
 * Both knobs exist for the containerised dev stack (docker-compose.dev.yaml) and
 * are unset everywhere else. The proxy reproduces what nginx does in production
 * — serve the API under /api, stripped before it reaches the backend — so the
 * browser can stay on one origin while the backend lives on the compose
 * network. Polling is needed because a bind mount delivers no filesystem events
 * to a Linux container on a macOS or Windows host.
 */
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET;
const watchPolling = process.env.VITE_WATCH_POLLING === 'true';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(rootDir, 'src'),
    },
  },
  server: {
    port: 3000,
    watch: watchPolling ? { usePolling: true } : undefined,
    proxy: apiProxyTarget
      ? {
          '/api': {
            target: apiProxyTarget,
            changeOrigin: true,
            rewrite: (requestPath) => requestPath.replace(/^\/api/, ''),
          },
        }
      : undefined,
  },
  preview: {
    port: 3000,
  },
  build: {
    rolldownOptions: {
      output: {
        /*
         * Dependencies change far less often than the app does. Splitting them
         * out means a release only invalidates the app chunk, so a returning
         * phone re-downloads a few kilobytes instead of the whole bundle.
         */
        codeSplitting: {
          groups: [
            { name: 'mantine', test: /[\\/]node_modules[\\/](@mantine|@tabler)[\\/]/ },
            {
              name: 'react',
              test: /[\\/]node_modules[\\/](react|react-dom|scheduler|react-router)[\\/]/,
            },
            { name: 'vendor', test: /[\\/]node_modules[\\/]/ },
          ],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
});
