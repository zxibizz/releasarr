import { useMemo, useState } from 'react';

import type { MediaRequest } from '@/types';

/** Languages we prefer when the user has not picked one explicitly. */
const PREFERRED_LANGUAGES = ['rus', 'eng'];

export const collectLanguages = (requests: MediaRequest[]): string[] => {
  const languages = new Set<string>();
  requests.forEach((request) => {
    Object.keys(request.localizations ?? {}).forEach((language) => {
      if (language) {
        languages.add(language);
      }
    });
  });
  return [...languages].sort();
};

export const localizeRequest = <T extends MediaRequest>(request: T, language: string | null): T => {
  const localization = language ? request.localizations?.[language] : undefined;
  if (!localization) {
    return request;
  }

  return {
    ...request,
    title: localization.title ?? request.title,
    overview: localization.overview ?? request.overview,
  };
};

const pickDefaultLanguage = (available: string[]): string | null => {
  if (available.length === 0) {
    return null;
  }
  return PREFERRED_LANGUAGES.find((language) => available.includes(language)) ?? available[0];
};

/**
 * Tracks the selected localization language, falling back to a preferred
 * language whenever the current selection is no longer available.
 */
export function useLanguageSelection(requests: MediaRequest[]) {
  const availableLanguages = useMemo(() => collectLanguages(requests), [requests]);
  const [selected, setSelected] = useState<string | null>(null);

  const language =
    selected && availableLanguages.includes(selected)
      ? selected
      : pickDefaultLanguage(availableLanguages);

  return { availableLanguages, language, setLanguage: setSelected };
}
