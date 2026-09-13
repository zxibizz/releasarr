import type { MediaType, RootFolder } from '../src/types';

/**
 * A stand-in for TVDB and TMDB. Each entry carries the seasons the *arr app
 * would report, plus an optional library id so the merged "already in Sonarr"
 * and "already requested" states can both be exercised without a real Sonarr.
 */
export interface DiscoverCatalogueEntry {
  type: MediaType;
  provider_id: number;
  title: string;
  year: number;
  overview: string;
  poster_url: string | null;
  /** The Sonarr/Radarr id, when the *arr app already holds this media. */
  library_id?: number;
  seasons?: number[];
  /** Seasons Sonarr monitors, for media already in the library. */
  monitored_seasons?: number[];
  /** Whether Sonarr monitors seasons announced after the series was added. */
  monitor_new_seasons?: boolean;
  /**
   * Translated titles and overviews keyed by 3-letter language code, as TVDB
   * reports them. Entries without one stand in for media the provider has no
   * translation for, which the search has to fall back gracefully from.
   */
  translations?: Record<string, { title: string; overview: string }>;
}

export const DISCOVER_CATALOGUE: DiscoverCatalogueEntry[] = [
  {
    type: 'series',
    provider_id: 121361,
    title: 'Game of Thrones',
    year: 2011,
    overview: 'Noble families fight for control of the Iron Throne.',
    poster_url: 'https://placehold.co/300x450?text=Game+of+Thrones',
    seasons: [0, 1, 2, 3, 4, 5, 6, 7, 8],
    translations: {
      rus: {
        title: 'Игра престолов',
        overview: 'Знатные семьи борются за Железный трон.',
      },
    },
  },
  {
    type: 'series',
    provider_id: 81189,
    // Already in Sonarr, and seasons 1 and 2 already have requests in the mock
    // request data, which is matched by title.
    title: 'Breaking Bad',
    year: 2008,
    overview: 'A chemistry teacher turns to manufacturing methamphetamine.',
    poster_url: 'https://placehold.co/300x450?text=Breaking+Bad',
    library_id: 12,
    seasons: [0, 1, 2, 3, 4, 5],
    monitored_seasons: [1, 2],
    monitor_new_seasons: true,
    translations: {
      rus: {
        title: 'Во все тяжкие',
        overview: 'Учитель химии начинает производить метамфетамин.',
      },
    },
  },
  {
    type: 'series',
    provider_id: 371980,
    title: 'Severance',
    year: 2022,
    overview: 'Employees undergo a memory-severing procedure.',
    poster_url: 'https://placehold.co/300x450?text=Severance',
    seasons: [1, 2],
  },
  {
    type: 'series',
    provider_id: 366524,
    title: 'Silo',
    year: 2023,
    overview: 'The last of humanity lives in a giant underground silo.',
    poster_url: null,
    seasons: [1, 2],
  },
  {
    type: 'movie',
    provider_id: 329865,
    title: 'Arrival',
    year: 2016,
    overview: 'A linguist is recruited to communicate with alien visitors.',
    poster_url: 'https://placehold.co/300x450?text=Arrival',
    translations: {
      rus: {
        title: 'Прибытие',
        overview: 'Лингвиста привлекают к общению с пришельцами.',
      },
    },
  },
  {
    type: 'movie',
    provider_id: 155,
    title: 'The Dark Knight',
    year: 2008,
    overview: 'Batman raises the stakes in his war on crime.',
    poster_url: 'https://placehold.co/300x450?text=The+Dark+Knight',
    library_id: 31,
    translations: {
      rus: {
        title: 'Тёмный рыцарь',
        overview: 'Бэтмен поднимает ставки в войне с преступностью.',
      },
    },
  },
  {
    type: 'movie',
    provider_id: 693134,
    title: 'Dune: Part Two',
    year: 2024,
    overview: 'Paul Atreides unites with the Fremen to seek revenge.',
    poster_url: null,
  },
];

/** The mock only speaks the two languages the UI does. */
const LANGUAGE_CODES: Record<string, string> = { en: 'eng', ru: 'rus' };

const toThreeLetterLanguage = (code: string | null | undefined): string | null => {
  const normalized = code?.trim().toLowerCase().split('-')[0];
  if (!normalized) {
    return null;
  }
  return LANGUAGE_CODES[normalized] ?? (normalized.length === 3 ? normalized : null);
};

/** Show the entry in the asked-for language, falling back to what it was written in. */
export const localizeEntry = (
  entry: DiscoverCatalogueEntry,
  language: string | null | undefined,
): { title: string; overview: string } => {
  const code = toThreeLetterLanguage(language);
  const translation = code ? entry.translations?.[code] : undefined;
  return {
    title: translation?.title ?? entry.title,
    overview: translation?.overview ?? entry.overview,
  };
};

export const DISCOVER_ROOT_FOLDERS: Record<MediaType, RootFolder[]> = {
  series: [
    { path: '/media/tv', free_space: 812_000_000_000 },
    { path: '/media/tv-4k', free_space: 214_000_000_000 },
  ],
  movie: [
    { path: '/media/movies', free_space: 1_400_000_000_000 },
    { path: '/media/movies-4k', free_space: 98_000_000_000 },
  ],
};
