import { useSyncExternalStore } from 'react';

/**
 * `navigator.onLine` only reports whether an interface is up, never whether the
 * server is reachable, so this is a hint rather than a fact. It is the same
 * hint TanStack Query's online manager uses, which is the point: the banner and
 * the paused polls can never disagree about being offline.
 */
const subscribe = (onChange: () => void): (() => void) => {
  window.addEventListener('online', onChange);
  window.addEventListener('offline', onChange);
  return () => {
    window.removeEventListener('online', onChange);
    window.removeEventListener('offline', onChange);
  };
};

const getSnapshot = (): boolean => navigator.onLine;

export function useOnlineStatus(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot);
}
