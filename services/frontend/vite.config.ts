import path from 'node:path';
import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react-swc';
import { VitePWA } from 'vite-plugin-pwa';
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
  plugins: [
    react(),
    /*
     * `prompt`, not `autoUpdate`: a new build is announced by
     * `src/pwa/UpdatePrompt.tsx` so it can be taken on the spot, and the waiting
     * worker takes over by itself on the next cold start if it is not.
     */
    VitePWA({
      registerType: 'prompt',
      // Registration is the virtual module that UpdatePrompt imports. Injecting
      // a registrar into index.html as well would register the worker twice.
      injectRegister: null,
      // The icons are already covered by `globPatterns` below, and this would
      // otherwise add a second precache entry for each one.
      includeManifestIcons: false,
      /*
       * The worker exists only in a production build. In dev it would outlive a
       * screenshot run in the harness' browser profile and serve stale assets
       * into the next capture.
       */
      devOptions: { enabled: false },
      manifest: {
        id: '/',
        name: 'Releasarr',
        short_name: 'Releasarr',
        description: 'Orchestrates media requests across Sonarr, Radarr, Prowlarr and qBittorrent.',
        // A manifest is a static file, so it cannot follow the in-app language
        // switch the way the rest of the UI does.
        lang: 'en',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        orientation: 'any',
        /*
         * Both match the body background in styles/global.css so the splash
         * screen, the status bar and the first painted frame are one colour.
         */
        background_color: '#0f172a',
        theme_color: '#0f172a',
        icons: [
          { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'maskable-icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // `webmanifest` is left out on purpose: the plugin adds the manifest to
        // the precache itself, and globbing it as well lists it twice.
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        /*
         * `sw.js` is written after the precache manifest is computed, so without
         * this a build picks up the previous build's worker and precaches it.
         */
        globIgnores: ['**/*.map', '**/sw.js', '**/workbox-*.js'],
        navigateFallback: 'index.html',
        /*
         * Nothing under /api is cached, here or at runtime. Responses are
         * authenticated and the refresh cookie rotates exactly once per use, so
         * replaying one looks to the backend like a stolen token — hence the
         * denylist, and hence the deliberate absence of a `runtimeCaching`
         * block.
         */
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
        skipWaiting: false,
        clientsClaim: false,
      },
    }),
  ],
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
