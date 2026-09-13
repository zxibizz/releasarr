import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import type { AppLocale } from '@/locales/resources';
import type { MediaRequest } from '@/types';

/**
 * The metadata language each UI language reads titles in. Requests key their
 * translations by the three-letter codes the backend's `metadata_languages`
 * setting names, which the two-letter UI locales have to be mapped onto.
 */
const METADATA_LANGUAGES: Record<AppLocale, string> = { en: 'eng', ru: 'rus' };

/** The metadata language Sonarr and Radarr report in, as the backend has it. */
const DEFAULT_METADATA_LANGUAGE = 'eng';

/**
 * Each metadata language under its own name. Not translated, and not the
 * `nav.languages` names: a control that offers a title in a language should say
 * which language in that language, whatever the interface is set to.
 */
const LANGUAGE_ENDONYMS: Record<string, string> = { eng: 'English', rus: 'Русский' };

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

/**
 * The metadata language to read requests in, taken from the UI language.
 *
 * A request without a translation in it keeps the title and overview the *arr
 * app reported, rather than falling back to some other language: a Russian
 * title on an English page is more surprising than an untranslated one.
 */
export function useMetadataLanguage(): string | null {
  const { i18n } = useTranslation();
  const locale = i18n.language?.split('-')[0]?.toLowerCase() as AppLocale | undefined;
  return (locale && METADATA_LANGUAGES[locale]) ?? null;
}

export interface RequestTitle {
  language: string;
  /** The language's own name, for a control that fills this title in. */
  label: string;
  title: string;
}

/**
 * The titles a request is known by: the one Sonarr or Radarr reported, and the
 * translation the UI is reading it under. An indexer carries releases named
 * either way and which one a given release used cannot be known in advance, so
 * a search has to be able to switch between them.
 *
 * A request whose metadata provider offered no translations has only its own
 * title, which is the *arr app's — the same assumption the backend makes in
 * treating `eng` as the home for the values those apps report.
 */
export function useRequestTitles(request: MediaRequest | null | undefined): RequestTitle[] {
  const metadataLanguage = useMetadataLanguage();

  return useMemo(() => {
    if (!request) {
      return [];
    }

    const languages = [DEFAULT_METADATA_LANGUAGE, metadataLanguage].filter(
      (language): language is string => Boolean(language),
    );

    const titles: RequestTitle[] = [];
    for (const language of languages) {
      const localized = request.localizations?.[language]?.title;
      const title = localized ?? (language === DEFAULT_METADATA_LANGUAGE ? request.title : null);
      // Two languages the provider translated the same way are one choice.
      if (!title || titles.some((existing) => existing.title === title)) {
        continue;
      }
      titles.push({
        language,
        label: LANGUAGE_ENDONYMS[language] ?? language.toUpperCase(),
        title,
      });
    }
    return titles;
  }, [metadataLanguage, request]);
}
