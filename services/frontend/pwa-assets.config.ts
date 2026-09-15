import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config';

/*
 * Nothing here is padded, and that is the point.
 *
 * `minimal-2023` insets the plain icons by 5% and pads Apple and maskable with
 * sharp's default white — which lands on a home screen as a pale frame around
 * the tile. Padding the maskable variant is also only useful when the artwork
 * runs to the canvas edge: it shrinks the art into the safe zone and fills the
 * gap with a flat colour, which here shows as a square seam against the art's
 * own gradient. The safe zone is already respected by the source itself, so
 * every variant is a full-bleed render and only the declared purpose differs.
 *
 * Regenerate with `npm run pwa:assets`; the results are committed, so an ordinary
 * build needs neither this file nor the generator.
 */
const background = '#0f172a';

export default defineConfig({
  headLinkOptions: { preset: '2023' },
  preset: {
    ...minimal2023Preset,
    /*
     * Spelled out rather than spread from the preset: `minimal2023Preset`
     * defines no `resizeOptions`, the generator's own default background is
     * white, and omitting `fit` would drop it.
     *
     * `padding: 0` leaves the resize nothing to letterbox, so these colours
     * never reach the file today — they are what would show if a future source
     * were not square, and neither variant may fall back to the white default.
     */
    transparent: {
      ...minimal2023Preset.transparent,
      padding: 0,
      resizeOptions: { fit: 'contain', background: 'transparent' },
    },
    maskable: {
      ...minimal2023Preset.maskable,
      padding: 0,
      resizeOptions: { fit: 'contain', background },
    },
    apple: {
      ...minimal2023Preset.apple,
      padding: 0,
      resizeOptions: { fit: 'contain', background },
    },
  },
  images: ['public/favicon.svg'],
});
