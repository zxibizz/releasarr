import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config';

/*
 * `minimal-2023` pads the maskable and Apple icons with sharp's default white,
 * which shows as a pale ring wherever a launcher masks the icon to a circle.
 * The source art is already a full-bleed square with its glyph inside the safe
 * zone, so those two variants are padded with the app's own background instead.
 *
 * Regenerate with `npm run pwa:assets`; the results are committed, so a normal
 * build never needs this file or the generator.
 */
const background = '#0f172a';

export default defineConfig({
  headLinkOptions: { preset: '2023' },
  preset: {
    ...minimal2023Preset,
    maskable: {
      ...minimal2023Preset.maskable,
      resizeOptions: { ...minimal2023Preset.maskable.resizeOptions, background },
    },
    apple: {
      ...minimal2023Preset.apple,
      resizeOptions: { ...minimal2023Preset.apple.resizeOptions, background },
    },
  },
  images: ['public/favicon.svg'],
});
