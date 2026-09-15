import { spawn, type ChildProcess } from 'node:child_process';
import process from 'node:process';

import {
  chromium,
  type Browser,
  type BrowserContext,
  type Locator,
  type Page,
} from 'playwright-core';

const APP_URL = 'http://localhost:3000';
const MOCK_HEALTH_URL = 'http://localhost:8001/__health';
const MOCK_API_URL = 'http://localhost:8001/api';
const SERVER_START_TIMEOUT_MS = 90_000;

/**
 * Kills animation, transitions and the text caret. Mantine transitions mean an
 * otherwise-identical page can differ between runs, and a blinking caret in a
 * filled search box shows up in roughly half of captures.
 *
 * Notifications are hidden outright. They are transient chrome that no shot
 * wants, and they arrive on their own schedule - dismissing them by clicking
 * races whatever toast fires next, which is how a "Sync finished" toast ended
 * up sitting over the tasks page header.
 */
const STILLNESS_CSS = `
  *, *::before, *::after {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
    scroll-behavior: auto !important;
  }
  * { caret-color: transparent !important; }
  .mantine-Notifications-root, .mantine-Notification-root { display: none !important; }
`;

async function isUp(url: string): Promise<boolean> {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(1_500) });
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForUp(url: string, label: string, deadline: number): Promise<void> {
  while (Date.now() < deadline) {
    if (await isUp(url)) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  throw new Error(`${label} did not come up at ${url}`);
}

export interface Servers {
  /** Base URL the app is served from. */
  url: string;
  stop: () => Promise<void>;
}

/**
 * Reuses an already-running `npm run dev:mock` when it finds one, so capturing
 * while developing does not fight the dev server for the port.
 */
export async function startServers(): Promise<Servers> {
  if (await isUp(APP_URL)) {
    console.log('Reusing the dev server already on :3000');
    return { url: APP_URL, stop: async () => {} };
  }

  console.log('Starting the mock API and dev server...');
  const child: ChildProcess = spawn('npm', ['run', 'dev:mock'], {
    // Own process group, so stop() can take the whole concurrently tree with it.
    detached: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  let log = '';
  child.stdout?.on('data', (chunk: Buffer) => {
    log += chunk.toString();
  });
  child.stderr?.on('data', (chunk: Buffer) => {
    log += chunk.toString();
  });

  let exited = false;
  child.on('exit', () => {
    exited = true;
  });

  const stop = async (): Promise<void> => {
    if (exited || child.pid === undefined) {
      return;
    }
    try {
      process.kill(-child.pid, 'SIGTERM');
    } catch {
      // Already gone.
    }
  };

  try {
    const deadline = Date.now() + SERVER_START_TIMEOUT_MS;
    await waitForUp(MOCK_HEALTH_URL, 'Mock API', deadline);
    await waitForUp(APP_URL, 'Dev server', deadline);
  } catch (error) {
    await stop();
    throw new Error(`${(error as Error).message}\n\nServer output:\n${log}`, { cause: error });
  }

  return { url: APP_URL, stop };
}

/**
 * `playwright-core` is deliberate: the full `playwright` package downloads a
 * browser on every `npm install`, which is a steep price for a tool that runs
 * when the README needs new images. So find a browser rather than ship one.
 */
export async function launchBrowser(headed: boolean): Promise<Browser> {
  const headless = !headed;
  const executablePath = process.env.RELEASARR_CHROMIUM;

  if (executablePath) {
    return chromium.launch({ headless, executablePath });
  }

  const attempts: Array<() => Promise<Browser>> = [
    () => chromium.launch({ headless }),
    () => chromium.launch({ headless, channel: 'chrome' }),
  ];

  const failures: string[] = [];
  for (const attempt of attempts) {
    try {
      return await attempt();
    } catch (error) {
      failures.push((error as Error).message.split('\n')[0]);
    }
  }

  throw new Error(
    [
      'No usable Chromium found. Either install the pinned browser:',
      '',
      '  npx playwright install chromium',
      '',
      'or point at one you already have:',
      '',
      '  RELEASARR_CHROMIUM=/path/to/chrome npm run screenshots',
      '',
      `Tried: ${failures.join(' | ')}`,
    ].join('\n'),
  );
}

export async function createContext(
  browser: Browser,
  viewport: { width: number; height: number },
  deviceScaleFactor: number,
): Promise<BrowserContext> {
  return browser.newContext({
    viewport,
    deviceScaleFactor,
    colorScheme: 'dark',
    reducedMotion: 'reduce',
  });
}

/**
 * Call after navigating. An init script would be the tidier place for this,
 * but it runs against an empty document and the DOMContentLoaded handler it
 * has to fall back to did not reliably land the stylesheet. A shot navigates
 * once and then stays inside the SPA, so injecting here is enough.
 */
export async function applyStillness(page: Page): Promise<void> {
  await page.addStyleTag({ content: STILLNESS_CSS });
}

/**
 * Signs the context in against the mock API before it opens a page.
 *
 * The app keeps its access token in memory, so a brand-new context has no
 * session until it bootstraps one off the refresh cookie. Logging in through
 * the API puts that cookie in the context's jar, exactly as a returning
 * browser has it; driving the login form instead would make every shot start
 * with a login, and leave the page the form navigated away from behind.
 */
export async function signIn(context: BrowserContext): Promise<void> {
  const url = `${MOCK_API_URL}/auth/login`;
  const response = await context.request.post(url, {
    data: { username: 'admin', password: 'admin', remember_me: false },
  });

  if (!response.ok()) {
    throw new Error(`Mock sign-in failed at ${url}: ${response.status()} ${await response.text()}`);
  }
}

export interface SettleOptions {
  /**
   * Skips the wait for spinners to clear. Needed where the spinner is the
   * point: on the tasks page, waiting for it to go away means waiting for the
   * jobs to finish, and the running queue is exactly what the shot is of.
   */
  allowSpinners?: boolean;
}

/**
 * Waits for the page to stop moving: network quiet, no spinners, fonts loaded,
 * and one painted frame. This is what the old script's `waitForTimeout(2500)`
 * calls were approximating.
 */
export async function settle(page: Page, options: SettleOptions = {}): Promise<void> {
  await page.waitForLoadState('networkidle');

  if (!options.allowSpinners) {
    const busy = page.locator('.mantine-Loader-root, .mantine-Skeleton-root');
    try {
      await busy.first().waitFor({ state: 'hidden', timeout: 10_000 });
    } catch {
      // No loader appeared, or one is permanently visible; either way, carry on.
    }
  }

  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(() => resolve(null)));
  });
}

/**
 * Waits for a control to become enabled. Useful where a button unlocks once a
 * query lands: that is a far better signal that the page is worth
 * photographing than any amount of waiting for the network to go quiet, since
 * React Query fires its requests well after the load event.
 */
export async function waitForEnabled(locator: Locator, timeoutMs = 15_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  await locator.waitFor({ state: 'visible', timeout: timeoutMs });

  while (Date.now() < deadline) {
    if (await locator.isEnabled()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }

  throw new Error('Timed out waiting for a control to become enabled');
}

/**
 * Scrolls so `text` sits `offset` pixels below the top of the viewport.
 * `scrollIntoViewIfNeeded` parks the element at the bottom edge, which framed
 * the heading correctly but cropped everything it was labelling.
 */
export async function scrollTextIntoView(page: Page, text: string, offset = 90): Promise<void> {
  const target = page.getByText(text, { exact: true }).first();
  await target.waitFor({ state: 'visible' });
  await target.evaluate((element, top: number) => {
    window.scrollTo({ top: element.getBoundingClientRect().top + window.scrollY - top });
  }, offset);
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => resolve(null))),
  );
}

