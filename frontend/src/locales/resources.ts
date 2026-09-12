import type { Resource } from 'i18next';

export const defaultNS = 'translation';

export const resources = {
  en: {
    translation: {
      nav: {
        requests: 'Requests',
        languageLabel: 'Select language',
        languages: {
          en: 'English',
          ru: 'Русский',
        },
      },
      common: {
        tryAgain: 'Try Again',
        backToRequests: '← Back to Requests',
        close: 'Close',
        cancel: 'Cancel',
      },
      mediaType: {
        movie: 'Movie',
        series: 'Series',
      },
      status: {
        pending: 'Pending',
        searching: 'Searching',
        downloading: 'Downloading',
        seeding: 'Seeding',
        completed: 'Completed',
        failed: 'Failed',
      },
      requestCard: {
        posterAlt: '{{title}} poster',
        season: 'Season {{season}}',
        episodes_one: '{{count}} episode',
        episodes_other: '{{count}} episodes',
        createdAt: 'Created {{date}}',
      },
      mediaInfo: {
        labels: {
          type: 'Type',
          created: 'Created',
          updated: 'Updated',
          series: 'Series',
          episodes: 'Episodes',
        },
        sections: {
          genres: 'Genres',
          overview: 'Overview',
        },
        episodes_one: '{{count}} episode',
        episodes_other: '{{count}} episodes',
      },
      requestsList: {
        title: 'Media Requests',
        subtitle: 'Track and manage your media server requests',
        searchPlaceholder: 'Search requests…',
        sortAriaLabel: 'Sort requests',
        refreshing: 'Refreshing data…',
        filters: {
          all: 'All',
          movies: 'Movies',
          series: 'Series',
        },
        sort: {
          created_desc: 'Newest first',
          created_asc: 'Oldest first',
          title_asc: 'Title A → Z',
          title_desc: 'Title Z → A',
        },
        stats: {
          total: 'Total Requests',
          movies: 'Movies',
          series: 'Series',
          completed: 'Completed',
        },
        headings: {
          all: 'All Requests',
          filtered: '{{label}} Requests',
        },
        resultsCount_one: '{{count}} request',
        resultsCount_other: '{{count}} requests',
        empty: {
          title: 'No requests found',
          description: 'No media requests have been created yet.',
        },
        emptyFiltered: {
          title: 'No matching requests',
          description: 'Try adjusting your filters or search query to find more results.',
        },
        error: {
          title: 'Unable to load requests',
          description: 'We could not retrieve the latest requests from the server.',
          fallbackTitle: 'Error loading requests',
        },
      },
      notFound: {
        title: 'Page not found',
        description:
          "The page you're looking for doesn't exist or may have moved. Let's get you back to the requests dashboard.",
      },
      routeError: {
        fallbackDescription: 'An unexpected error occurred while rendering this page.',
        requestFailed: 'Request failed',
        routerErrorLabel: 'Router Error',
        clientErrorLabel: 'Client Error',
        genericTitle: 'Something went wrong',
        genericDescription: 'We hit an unexpected issue while loading this view.',
        unexpectedTitle: 'Unexpected Error',
        errorDetails: 'Error details',
      },
      requestHeader: {
        subtitle: {
          movie: 'Movie request details',
          series: 'Series request details',
        },
      },
      localization: {
        selectorLabel: 'Metadata language',
        defaultOption: 'Original metadata',
        languageNames: {
          eng: 'English',
          rus: 'Русский',
        },
      },
      requestActions: {
        title: '🔧 Request Actions',
      },
      requestReleases: {
        title: '📦 Releases',
        subtitle: 'Releases linked to this request',
      },
      releasesList: {
        title: 'Releases',
        error: {
          title: 'Unable to load releases',
          description: 'We could not retrieve releases for this request.',
          fallbackTitle: 'Error loading releases',
        },
        refreshing: 'Refreshing releases…',
      },
      releaseSearch: {
        title: '🔍 Search Release Sources',
        instructions: 'Enter a title or identifier and press the search button to fetch release candidates.',
        placeholder: 'Search release sources for "{{title}}"…',
        ariaLabel: 'Search releases for {{title}}',
        actions: {
          runSearch: 'Run release search',
          search: 'Search',
          searching: 'Searching…',
          clear: 'Clear',
          queueDownload: 'Queue download for {{name}}',
        },
        links: {
          magnet: 'Magnet link ↗',
          info: 'View info ↗',
          torrent: 'Torrent file ↗',
        },
        loading: {
          queueing: 'Queuing…',
        },
        download: 'Download',
        toasts: {
          searchFailedTitle: 'Search failed',
          searchFailedFallback: 'Search failed',
          downloadQueuedTitle: 'Download queued',
          downloadQueuedFallback: '{{name}} queued for download',
          downloadFailedTitle: 'Download failed',
          downloadFailedFallback: 'Failed to queue download',
        },
        results: {
          heading: 'Search Results',
          summary: '{{count}} results for "{{query}}"',
          summaryWithTotal: '{{count}} of {{total}} results for "{{query}}"',
          updating: 'Updating…',
        },
        sort: {
          label: 'Sort by',
          directionLabel: 'Order',
          fields: {
            seeders: 'Seeders',
            leechers: 'Leechers',
            size: 'Size',
          },
          directions: {
            desc: 'High → Low',
            asc: 'Low → High',
          },
        },
        filters: {
          source: {
            label: 'Source',
            all: 'All sources',
          },
        },
        quality: {
          unknown: 'Unknown',
        },
        empty: {
          title: 'No release sources found',
          description: 'Try adjusting your search terms or check back later.',
        },
      },
      releaseCard: {
        aria: {
          viewFiles: 'View files',
          toggleDetails: 'Toggle details',
          delete: 'Delete release',
        },
        buttons: {
          files: 'Files',
          pause: 'Pause',
          resume: 'Resume',
        },
        dialog: {
          title: 'Delete release',
          body: 'This will remove the release and its file mappings from the request. Are you sure you want to continue?',
          confirm: 'Delete',
        },
      },
      requestPage: {
        errors: {
          loadRequestTitle: 'Unable to load this request',
          loadRequestDescription: 'We could not retrieve the latest data for this request.',
          loadLogsTitle: 'Unable to load logs',
          loadLogsDescription: 'We could not retrieve activity logs for this request.',
          notFoundTitle: 'Request not found',
          notFoundDescription: 'The requested media could not be found.',
        },
        manualSearch: {
          unavailableTitle: 'Manual search unavailable',
          missingDetails: 'Missing request details; cannot build search query.',
          emptyDescription: 'Request title is empty; please update the request first.',
        },
        toasts: {
          refreshPendingTitle: 'Refreshing status',
          refreshPendingDescription: 'Checking for the latest updates...',
          refreshSuccessTitle: 'Status refreshed',
          refreshSuccessDescription: 'Request details and releases are up to date.',
          refreshErrorTitle: 'Refresh failed',
          refreshErrorFallback: 'Failed to refresh request',
        },
        actions: {
          refresh: {
            title: 'Refresh Status',
            description: 'Check for updates on this request',
            loadingText: 'Refreshing…',
          },
          manualSearch: {
            title: 'Manual Search',
            description: 'Trigger a manual search for releases',
          },
          logs: {
            title: 'View Logs',
            description: 'Check processing logs for this request',
          },
        },
      },
      requestLogsModal: {
        title: 'Logs for {{title}}',
        empty: 'No logs available for this request.',
        refreshing: 'Refreshing logs…',
        context: 'Context',
        stackTrace: {
          show: 'View stack trace',
          hide: 'Hide stack trace',
        },
      },
    },
  },
  ru: {
    translation: {
      nav: {
        requests: 'Запросы',
        languageLabel: 'Выберите язык',
        languages: {
          en: 'Английский',
          ru: 'Русский',
        },
      },
      common: {
        tryAgain: 'Повторить попытку',
        backToRequests: '← Назад к запросам',
        close: 'Закрыть',
        cancel: 'Отмена',
      },
      mediaType: {
        movie: 'Фильм',
        series: 'Сериал',
      },
      status: {
        pending: 'В ожидании',
        searching: 'Поиск',
        downloading: 'Загрузка',
        seeding: 'Раздача',
        completed: 'Готово',
        failed: 'Ошибка',
      },
      requestCard: {
        posterAlt: 'Постер «{{title}}»',
        season: '{{season}} сезон',
        episodes_one: '{{count}} серия',
        episodes_few: '{{count}} серии',
        episodes_many: '{{count}} серий',
        episodes_other: '{{count}} серий',
        createdAt: 'Создано {{date}}',
      },
      mediaInfo: {
        labels: {
          type: 'Тип',
          created: 'Создано',
          updated: 'Обновлено',
          series: 'Сериал',
          episodes: 'Эпизоды',
        },
        sections: {
          genres: 'Жанры',
          overview: 'Описание',
        },
        episodes_one: '{{count}} серия',
        episodes_few: '{{count}} серии',
        episodes_many: '{{count}} серий',
        episodes_other: '{{count}} серий',
      },
      requestsList: {
        title: 'Запросы медиатеки',
        subtitle: 'Отслеживайте и управляйте запросами к медиасерверу',
        searchPlaceholder: 'Поиск запросов…',
        sortAriaLabel: 'Сортировать запросы',
        refreshing: 'Обновляем данные…',
        filters: {
          all: 'Все',
          movies: 'Фильмы',
          series: 'Сериалы',
        },
        sort: {
          created_desc: 'Сначала новые',
          created_asc: 'Сначала старые',
          title_asc: 'Название A → Z',
          title_desc: 'Название Z → A',
        },
        stats: {
          total: 'Всего запросов',
          movies: 'Фильмы',
          series: 'Сериалы',
          completed: 'Завершено',
        },
        headings: {
          all: 'Все запросы',
          filtered: '{{label}}',
        },
        resultsCount_one: '{{count}} запрос',
        resultsCount_few: '{{count}} запроса',
        resultsCount_many: '{{count}} запросов',
        resultsCount_other: '{{count}} запросов',
        empty: {
          title: 'Запросы не найдены',
          description: 'Пока ещё не создано ни одного запроса.',
        },
        emptyFiltered: {
          title: 'Ничего не найдено',
          description: 'Измените фильтры или поисковый запрос, чтобы получить результаты.',
        },
        error: {
          title: 'Не удалось загрузить запросы',
          description: 'Не удалось получить последние запросы с сервера.',
          fallbackTitle: 'Ошибка загрузки запросов',
        },
      },
      notFound: {
        title: 'Страница не найдена',
        description:
          'Искомая страница не существует или была перемещена. Вернёмся на страницу запросов.',
      },
      routeError: {
        fallbackDescription: 'Произошла непредвиденная ошибка при отображении страницы.',
        requestFailed: 'Запрос не выполнен',
        routerErrorLabel: 'Ошибка роутера',
        clientErrorLabel: 'Ошибка клиента',
        genericTitle: 'Что-то пошло не так',
        genericDescription: 'При загрузке представления произошла непредвиденная ошибка.',
        unexpectedTitle: 'Непредвиденная ошибка',
        errorDetails: 'Подробности ошибки',
      },
      requestHeader: {
        subtitle: {
          movie: 'Детали запроса на фильм',
          series: 'Детали запроса на сериал',
        },
      },
      requestActions: {
        title: '🔧 Действия с запросом',
      },
      requestReleases: {
        title: '📦 Релизы',
        subtitle: 'Релизы, связанные с этим запросом',
      },
      releasesList: {
        title: 'Релизы',
        error: {
          title: 'Не удалось загрузить релизы',
          description: 'Не удалось получить релизы для этого запроса.',
          fallbackTitle: 'Ошибка загрузки релизов',
        },
        refreshing: 'Обновляем релизы…',
      },
      releaseSearch: {
        title: '🔍 Поиск релизов',
        instructions: 'Введите название или идентификатор и нажмите поиск, чтобы получить кандидатов.',
        placeholder: 'Поиск релизов для «{{title}}»…',
        ariaLabel: 'Поиск релизов для {{title}}',
        actions: {
          runSearch: 'Запустить поиск релизов',
          search: 'Поиск',
          searching: 'Идёт поиск…',
          clear: 'Очистить',
          queueDownload: 'Поставить в очередь «{{name}}»',
        },
        links: {
          magnet: 'Magnet-ссылка ↗',
          info: 'Подробнее ↗',
          torrent: 'Torrent-файл ↗',
        },
        loading: {
          queueing: 'Добавляем…',
        },
        download: 'Скачать',
        toasts: {
          searchFailedTitle: 'Поиск не удался',
          searchFailedFallback: 'Ошибка при запуске поиска',
          downloadQueuedTitle: 'Скачивание добавлено',
          downloadQueuedFallback: '«{{name}}» поставлен в очередь на скачивание',
          downloadFailedTitle: 'Не удалось добавить скачивание',
          downloadFailedFallback: 'Ошибка при добавлении в очередь',
        },
        results: {
          heading: 'Результаты поиска',
          summary: '{{count}} результатов для «{{query}}»',
          summaryWithTotal: '{{count}} из {{total}} результатов для «{{query}}»',
          updating: 'Обновляем…',
        },
        sort: {
          label: 'Сортировка',
          directionLabel: 'Порядок',
          fields: {
            seeders: 'Сиды',
            leechers: 'Личеры',
            size: 'Размер',
          },
          directions: {
            desc: 'По убыванию',
            asc: 'По возрастанию',
          },
        },
        filters: {
          source: {
            label: 'Источник',
            all: 'Все источники',
          },
        },
        quality: {
          unknown: 'Неизвестно',
        },
        empty: {
          title: 'Ничего не найдено',
          description: 'Измените поисковый запрос или попробуйте позже.',
        },
      },
      releaseCard: {
        aria: {
          viewFiles: 'Открыть файлы',
          toggleDetails: 'Показать детали',
          delete: 'Удалить релиз',
        },
        buttons: {
          files: 'Файлы',
          pause: 'Пауза',
          resume: 'Продолжить',
        },
        dialog: {
          title: 'Удалить релиз',
          body: 'Релиз и его связи с запросами будут удалены. Продолжить?',
          confirm: 'Удалить',
        },
      },
      requestPage: {
        errors: {
          loadRequestTitle: 'Не удалось загрузить запрос',
          loadRequestDescription: 'Не удалось получить актуальные данные по этому запросу.',
          loadLogsTitle: 'Не удалось загрузить логи',
          loadLogsDescription: 'Не удалось получить журналы обработки для этого запроса.',
          notFoundTitle: 'Запрос не найден',
          notFoundDescription: 'Не удалось найти указанную запись.',
        },
        manualSearch: {
          unavailableTitle: 'Ручной поиск недоступен',
          missingDetails: 'Недостаточно данных запроса, чтобы сформировать поисковый запрос.',
          emptyDescription: 'Название запроса пустое. Сначала обновите карточку запроса.',
        },
        toasts: {
          refreshPendingTitle: 'Обновляем статус',
          refreshPendingDescription: 'Проверяем наличие новых обновлений…',
          refreshSuccessTitle: 'Статус обновлён',
          refreshSuccessDescription: 'Данные запроса и релизов актуальны.',
          refreshErrorTitle: 'Не удалось обновить',
          refreshErrorFallback: 'Ошибка при обновлении запроса',
        },
        actions: {
          refresh: {
            title: 'Обновить статус',
            description: 'Проверить изменения по этому запросу',
            loadingText: 'Обновляем…',
          },
          manualSearch: {
            title: 'Ручной поиск',
            description: 'Запустить ручной поиск релизов',
          },
          logs: {
            title: 'Просмотреть логи',
            description: 'Открыть журналы обработки по запросу',
          },
        },
      },
      requestLogsModal: {
        title: 'Логи для {{title}}',
        empty: 'Для этого запроса пока нет логов.',
        refreshing: 'Обновляем логи…',
        context: 'Контекст',
        stackTrace: {
          show: 'Показать стек',
          hide: 'Скрыть стек',
        },
      },
    },
  },
} satisfies Resource;

export type AppLocale = keyof typeof resources;

export const supportedLocales = Object.keys(resources) as AppLocale[];
