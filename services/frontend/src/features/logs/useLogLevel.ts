import { useState } from 'react';

import { isLogLevel } from '@/features/logs/levels';
import type { RequestLogLevel } from '@/types';

const STORAGE_KEY = 'releasarr.logLevel';

const readStoredLevel = (): RequestLogLevel | undefined => {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isLogLevel(stored) ? stored : undefined;
  } catch {
    // localStorage can throw in private browsing modes.
    return undefined;
  }
};

/**
 * The severity the log view opens at, remembered between visits.
 *
 * It is a preference rather than part of a view, so it lives in storage instead
 * of the URL the way the process and task filters do: someone who only ever wants
 * errors wants them on every tab, in every link, and after every reload.
 */
export function useLogLevel() {
  const [level, setStoredLevel] = useState<RequestLogLevel | undefined>(readStoredLevel);

  const setLevel = (value: RequestLogLevel | undefined) => {
    setStoredLevel(value);
    try {
      if (value) {
        window.localStorage.setItem(STORAGE_KEY, value);
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // Persistence is best-effort.
    }
  };

  return { level, setLevel };
}
