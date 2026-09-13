import { useTranslation } from 'react-i18next';

import type { AppLocale } from '@/locales/resources';
import type { MediaRequest } from '@/types';

/**
 * The metadata language each UI language reads titles in. Requests key their
 * translations by the three-letter codes the backend's `metadata_languages`
 * setting names, which the two-letter UI locales have to be mapped onto.
 */
const METADATA_LANGUAGES: Record<AppLocale, string> = { en: 'eng', ru: 'rus' };

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
