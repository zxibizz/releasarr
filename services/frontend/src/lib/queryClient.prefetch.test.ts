import { afterEach, describe, expect, it, vi } from 'vitest';

import { prefetchWhenOnline } from '@/lib/queryClient';
import { setOnlineStatus } from '@/test/utils';

/*
 * The guard reads `navigator.onLine` — the same signal the offline screen and
 * the notice below it read — so the three can never disagree about being
 * offline.
 */
describe('prefetchWhenOnline', () => {
  afterEach(() => setOnlineStatus(true));

  it('runs the prefetch while there is a connection', async () => {
    setOnlineStatus(true);
    const load = vi.fn().mockResolvedValue(undefined);

    await prefetchWhenOnline(load);

    expect(load).toHaveBeenCalledTimes(1);
  });

  it('steps aside while the browser reports no connection', async () => {
    setOnlineStatus(false);
    const load = vi.fn().mockResolvedValue(undefined);

    await prefetchWhenOnline(load);

    expect(load).not.toHaveBeenCalled();
  });
});
