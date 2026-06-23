import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import {
  defaultNS,
  resources,
  supportedLocales,
  type AppLocale,
} from '@/locales/resources';

const STORAGE_KEY = 'releasarr.language';
const FALLBACK_LANGUAGE: AppLocale = 'en';

const isBrowser = typeof window !== 'undefined';

const resolveStoredLanguage = (): AppLocale | null => {
  if (!isBrowser) {
    return null;
  }
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return null;
    }
    return supportedLocales.includes(stored as AppLocale) ? (stored as AppLocale) : null;
  } catch {
    return null;
  }
};

const resolveNavigatorLanguage = (): AppLocale | null => {
  if (!isBrowser) {
    return null;
  }
  const navigatorLanguage = window.navigator.language || window.navigator.languages?.[0];
  if (!navigatorLanguage) {
    return null;
  }
  const normalized = navigatorLanguage.split('-')[0]?.toLowerCase();
  return supportedLocales.includes(normalized as AppLocale) ? (normalized as AppLocale) : null;
};

const initialLanguage: AppLocale =
  resolveStoredLanguage() ?? resolveNavigatorLanguage() ?? FALLBACK_LANGUAGE;

void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage,
  fallbackLng: FALLBACK_LANGUAGE,
  defaultNS,
  supportedLngs: supportedLocales,
  interpolation: {
    escapeValue: false,
  },
  returnNull: false,
});

if (isBrowser) {
  document.documentElement.lang = initialLanguage;
  i18n.on('languageChanged', (lng) => {
    document.documentElement.lang = lng;
    try {
      window.localStorage.setItem(STORAGE_KEY, lng);
    } catch {
      // ignore persistence errors
    }
  });
}

export default i18n;
