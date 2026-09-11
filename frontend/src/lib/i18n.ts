import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import { defaultNS, resources, supportedLocales, type AppLocale } from '@/locales/resources';

const STORAGE_KEY = 'releasarr.language';
const FALLBACK_LANGUAGE: AppLocale = 'en';

const isSupported = (value: string | undefined | null): value is AppLocale =>
  Boolean(value) && supportedLocales.includes(value as AppLocale);

const resolveInitialLanguage = (): AppLocale => {
  if (typeof window === 'undefined') {
    return FALLBACK_LANGUAGE;
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (isSupported(stored)) {
      return stored;
    }
  } catch {
    // localStorage can throw in private browsing modes; fall through to navigator.
  }

  const navigatorLanguage = window.navigator.language ?? window.navigator.languages?.[0];
  const normalized = navigatorLanguage?.split('-')[0]?.toLowerCase();
  return isSupported(normalized) ? normalized : FALLBACK_LANGUAGE;
};

const initialLanguage = resolveInitialLanguage();

void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage,
  fallbackLng: FALLBACK_LANGUAGE,
  defaultNS,
  supportedLngs: supportedLocales,
  interpolation: { escapeValue: false },
  returnNull: false,
});

if (typeof window !== 'undefined') {
  document.documentElement.lang = initialLanguage;
  i18n.on('languageChanged', (language) => {
    document.documentElement.lang = language;
    try {
      window.localStorage.setItem(STORAGE_KEY, language);
    } catch {
      // Persistence is best-effort.
    }
  });
}

export default i18n;
