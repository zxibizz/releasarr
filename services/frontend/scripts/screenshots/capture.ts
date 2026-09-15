/**
 * Captures the screenshots the root README embeds, against the mock API.
 *
 *   npm run screenshots                    # all of them
 *   npm run screenshots -- tasks requests  # just these
 *   npm run screenshots -- --list
 *   npm run screenshots -- --headed tasks  # watch it drive the UI
 *   npm run screenshots -- --url http://localhost:3000
 */
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import type { Browser } from 'playwright-core';

import {
  applyStillness,
  createContext,
  launchBrowser,
  settle,
  signIn,
  startServers,
  type Servers,
} from './harness';
import { shots, type Shot } from './shots';

const DEFAULT_VIEWPORT = { width: 1500, height: 980 };
/** Sharper than 1x without the file sizes a full 2x would put in the README. */
const DEVICE_SCALE_FACTOR = 1.1;
const DEFAULT_OUT_DIR = path.resolve(import.meta.dirname, '../../../../docs/screenshots');

interface Options {
  names: string[];
  list: boolean;
  headed: boolean;
  outDir: string;
  url?: string;
}

function parseArgs(argv: string[]): Options {
  const options: Options = {
    names: [],
    list: false,
    headed: false,
    outDir: DEFAULT_OUT_DIR,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    switch (arg) {
      case '--list':
        options.list = true;
        break;
      case '--headed':
        options.headed = true;
        break;
      case '--out':
        options.outDir = path.resolve(argv[(index += 1)]);
        break;
      case '--url':
        options.url = argv[(index += 1)];
        break;
      default:
        if (arg.startsWith('-')) {
          throw new Error(`Unknown flag: ${arg}`);
        }
        options.names.push(arg);
    }
  }

  return options;
}

function selectShots(names: string[]): Shot[] {
  if (names.length === 0) {
    return shots;
  }

  const unknown = names.filter((name) => !shots.some((shot) => shot.name === name));
  if (unknown.length > 0) {
    throw new Error(
      `Unknown shot(s): ${unknown.join(', ')}\nKnown: ${shots.map((shot) => shot.name).join(', ')}`,
    );
  }

  return shots.filter((shot) => names.includes(shot.name));
}

async function capture(browser: Browser, baseUrl: string, outDir: string, shot: Shot) {
  const context = await createContext(
    browser,
    shot.viewport ?? DEFAULT_VIEWPORT,
    DEVICE_SCALE_FACTOR,
  );

  try {
    const page = await context.newPage();
    await signIn(context);
    await page.goto(baseUrl + shot.route, { waitUntil: 'networkidle' });
    await applyStillness(page);
    await settle(page);
    await shot.prepare?.(page);

    const file = path.join(outDir, `${shot.name}.png`);
    await page.screenshot({ path: file });
    console.log(`  ${shot.name} -> ${path.relative(process.cwd(), file)}`);
  } finally {
    // A fresh context per shot keeps viewport overrides and any state a
    // prepare step leaves behind from leaking into the next image.
    await context.close();
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));

  if (options.list) {
    for (const shot of shots) {
      console.log(`${shot.name.padEnd(18)} ${shot.description}`);
    }
    return;
  }

  const selected = selectShots(options.names);
  await mkdir(options.outDir, { recursive: true });

  let servers: Servers | undefined;
  let browser: Browser | undefined;

  try {
    const baseUrl = options.url ?? (servers = await startServers()).url;
    browser = await launchBrowser(options.headed);

    console.log(`Capturing ${selected.length} shot(s) from ${baseUrl}`);
    for (const shot of selected) {
      await capture(browser, baseUrl, options.outDir, shot);
    }
  } finally {
    await browser?.close();
    await servers?.stop();
  }
}

main().catch((error: unknown) => {
  console.error(`\n${(error as Error).message}`);
  process.exitCode = 1;
});
