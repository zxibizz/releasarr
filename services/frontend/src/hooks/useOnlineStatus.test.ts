import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useOnlineStatus } from '@/hooks/useOnlineStatus';
import { setOnlineStatus } from '@/test/utils';

describe('useOnlineStatus', () => {
  beforeEach(() => setOnlineStatus(true));
  afterEach(() => setOnlineStatus(true));

  it('reports the connection state it starts in', () => {
    setOnlineStatus(false);

    const { result } = renderHook(() => useOnlineStatus());

    expect(result.current).toBe(false);
  });

  it('follows the browser in both directions', () => {
    const { result } = renderHook(() => useOnlineStatus());

    act(() => setOnlineStatus(false));
    expect(result.current).toBe(false);

    act(() => setOnlineStatus(true));
    expect(result.current).toBe(true);
  });

  it('stops listening once it unmounts', () => {
    const removeListener = vi.spyOn(window, 'removeEventListener');
    const { unmount } = renderHook(() => useOnlineStatus());

    unmount();

    expect(removeListener).toHaveBeenCalledWith('online', expect.any(Function));
    expect(removeListener).toHaveBeenCalledWith('offline', expect.any(Function));
    removeListener.mockRestore();
  });
});
