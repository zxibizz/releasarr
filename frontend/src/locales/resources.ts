import type { Resource } from 'i18next';

export const defaultNS = 'translation';

export const resources = {
  en: {
    translation: {
      nav: {
        requests: 'Requests',
        add: 'Add',
        system: 'System',
        openMenu: 'Open navigation menu',
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
        refresh: 'Refresh',
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
        queued: 'Queued',
        running: 'Running',
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
        filtersToggle: 'Filters',
        filtersToggleActive: 'Filters (active)',
        refreshing: 'Refreshing data…',
        filters: {
          typeLabel: 'Type',
          statusLabel: 'Status',
          active: 'In progress',
          all: 'All',
          anyStatus: 'Any',
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
          active: 'In Progress',
          filtered: '{{label}} Requests',
          withType: '{{status}} · {{type}}',
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
      discover: {
        title: 'Add Request',
        subtitle: 'Search TVDB or TMDB, then add the result to Sonarr or Radarr',
        searchPlaceholder: 'Search movies and series by title…',
        actions: {
          add: 'Add Request',
          addShort: 'Add',
          search: 'Search',
          request: 'Request',
          pickSeasons: 'Choose seasons',
          viewRequest: 'View request',
        },
        badges: {
          inLibrary: 'In library',
          requestedSeasons: 'Requested: {{seasons}}',
        },
        results: {
          heading: 'Results',
          count_one: '{{count}} result',
          count_other: '{{count}} results',
        },
        seasons: {
          label: 'Seasons',
          season: 'Season {{season}}',
          specials: 'Specials',
          selectAll: 'Select all',
          clearAll: 'Clear all',
          alreadyRequested: 'Already requested',
          alreadyDownloaded: 'Already downloaded in full',
          sonarrWillFetch: 'Sonarr will fetch this one as it airs',
          allCovered:
            'Sonarr already covers every season of this series, so only future seasons are left to choose.',
          newSeasons: 'New seasons',
          newSeasonsHint: 'Request future seasons of this series as they are announced.',
          none: 'No seasons are available for this series yet.',
          loadFailed: 'We could not load the seasons for this series.',
        },
        modal: {
          rootFolder: 'Library folder',
          rootFolderHint: 'Where Sonarr or Radarr will store the files.',
          rootFolderPlaceholder: 'Pick a folder',
          rootFolderOption: '{{path}} ({{free}} free)',
          rootFolderFailed: 'We could not load the available folders.',
          noRootFolders: 'No library folders are configured in Sonarr or Radarr.',
          inLibraryMovie: 'This movie is already in Radarr, so only monitoring will be enabled.',
          inLibrarySeries:
            'This series is already in Sonarr. Picking a season adds it to what Sonarr monitors; the seasons you leave alone keep the monitoring they have.',
          confirm: 'Add request',
          confirmMonitoring: 'Save monitoring',
        },
        added_one: 'Added {{count}} request',
        added_other: 'Added {{count}} requests',
        monitoringUpdated: 'Monitoring updated',
        addFailed: 'Failed to add request',
        empty: {
          title: 'No matches found',
          description: 'Try a different spelling, or search for the original title.',
        },
        start: {
          title: 'Search for something to request',
          description:
            'Movies and series are searched together, so you do not have to know which it is.',
        },
        error: {
          title: 'Search failed',
          description: 'We could not reach the metadata provider.',
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
      },
      releaseSearch: {
        placeholder: 'Search release sources for "{{title}}"…',
        ariaLabel: 'Search releases for {{title}}',
        tabs: {
          search: 'Search',
          manual: 'Add manually',
        },
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
            age: 'Age',
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
          toggle: 'Filters',
          toggleActive: 'Filters (active)',
          source: {
            label: 'Source',
            all: 'All sources',
          },
        },
        age: {
          unknown: 'Unknown age',
          today: 'Today',
          days_one: '{{count}} day',
          days_other: '{{count}} days',
        },
        empty: {
          title: 'No release sources found',
          description: 'Try adjusting your search terms or check back later.',
        },
      },
      manualRelease: {
        instructions:
          'Already have the release? Upload its .torrent file or paste a magnet link and it goes straight to the download client.',
        or: 'or',
        file: {
          label: 'Torrent file',
          description: 'The file list is read straight away, so files are mapped on arrival.',
          placeholder: 'Choose a .torrent file',
          invalid: 'That is not a .torrent file. Pick the torrent itself, not the media.',
        },
        magnet: {
          label: 'Magnet link',
          description: 'File names only arrive once the download client has the metadata.',
          placeholder: 'magnet:?xt=urn:btih:…',
          invalid: 'A magnet link must start with "magnet:".',
        },
        actions: {
          submit: 'Add release',
          clear: 'Clear',
        },
        toasts: {
          queuedTitle: 'Download queued',
          queuedDescription: 'The release was handed to the download client.',
          failedTitle: 'Could not add the release',
          failedFallback: 'Failed to add the release',
        },
      },
      releaseCard: {
        source: 'Source',
        progress: 'Progress',
        relatedRequests: 'Related requests',
        added: 'Added {{date}}',
        completed: 'Completed {{date}}',
        stats: {
          seeders: 'Seeders',
          leechers: 'Leechers',
          ratio: 'Ratio',
          health: 'Health',
        },
        files: {
          total_one: '{{count}} file',
          total_other: '{{count}} files',
          video_one: '{{count}} video',
          video_other: '{{count}} video',
          subtitle_one: '{{count}} subtitle',
          subtitle_other: '{{count}} subtitles',
        },
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
          remove: {
            title: 'Remove Request',
            description: 'Stop wanting this and unmonitor it',
          },
        },
        seasons: {
          manage: 'Manage seasons',
          modalTitle: 'Seasons of {{title}}',
          confirm: 'Save seasons',
          saved: 'Seasons updated',
          saveFailed: 'Could not update the seasons',
          unavailable:
            'Sonarr has not linked this request to a series yet, so its seasons cannot be managed.',
          removeDialog: {
            title: 'Stop monitoring seasons',
            body: 'Sonarr will stop monitoring {{seasons}}, and any requests for them will be removed. Files already downloaded are left alone.',
            confirm: 'Unmonitor and save',
          },
        },
        remove: {
          dialogTitle: 'Remove request',
          dialogBodySeries:
            'The request will be removed and Sonarr will stop monitoring this season. The series stays in your library, as do any files already downloaded.',
          dialogBodyMovie:
            'The request will be removed and Radarr will stop monitoring this movie. It stays in your library, as do any files already downloaded.',
          confirm: 'Remove request',
          removed: 'Request removed',
          failed: 'Could not remove the request',
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
      tasks: {
        toasts: {
          queued: 'Sync queued',
          finished: 'Sync finished',
          failedTitle: 'Sync failed',
          failedFallback: 'Some sync steps did not finish.',
          queueFailedTitle: 'Could not queue sync',
          queueFailedFallback: 'The server rejected the sync request.',
        },
        page: {
          title: 'Tasks',
          subtitle: 'Background work Releasarr runs for you, and what it has run recently.',
          runAll: 'Run all tasks',
          error: {
            title: 'Could not load tasks',
            description: 'The task list is unavailable right now.',
          },
          stalled: {
            title: 'Nothing is picking up queued tasks',
            description:
              'A task has been waiting for a while. The scheduler process may not be running.',
          },
        },
        kinds: {
          sonarr_sync: {
            name: 'Sonarr Sync',
            description: 'Pull wanted episodes and series from Sonarr.',
          },
          radarr_sync: {
            name: 'Radarr Sync',
            description: 'Pull wanted movies from Radarr.',
          },
          release_sync: {
            name: 'Refresh Downloads',
            description: 'Update download progress and state from the download client.',
          },
          export: {
            name: 'Import Finished',
            description: 'Import completed downloads into Sonarr and Radarr.',
          },
          regrab: {
            name: 'Regrab Outdated',
            description: 'Re-download releases the indexer has since replaced.',
          },
        },
        triggers: {
          api: 'Manual',
          download_client: 'Download client',
          schedule: 'Scheduled',
        },
        scheduled: {
          title: 'Scheduled',
          runNow: 'Run now',
          runTask: 'Run {{name}} now',
          never: 'Never',
          pendingFirstRun: 'On next start',
          lastRunFailed: 'The last scheduled run failed.',
          columns: {
            name: 'Name',
            interval: 'Interval',
            lastExecution: 'Last execution',
            lastDuration: 'Last duration',
            nextExecution: 'Next execution',
          },
        },
        queue: {
          title: 'Queue',
          description:
            'Runs you or your download client asked for. Scheduled runs are reported above.',
          count_one: '{{count}} run',
          count_other: '{{count}} runs',
          active_one: '{{count}} active',
          active_other: '{{count}} active',
          toggleDetails: 'Show details for {{name}}',
          empty: {
            title: 'No runs yet',
            description: 'Tasks you run manually will appear here with their output.',
          },
          columns: {
            name: 'Name',
            trigger: 'Trigger',
            queued: 'Queued',
            started: 'Started',
            duration: 'Duration',
            status: 'Status',
          },
        },
        output: {
          empty: 'This run did not report any details.',
          errorTitle: 'Error',
        },
      },
      logLevels: {
        info: 'Info',
        warning: 'Warning',
        error: 'Error',
      },
      taskLogs: {
        title: 'Logs',
        description: 'Everything the background tasks logged, newest first.',
        filterLabel: 'Filter by task',
        allTasks: 'All tasks',
        source: 'Source',
        toggleDetails: 'Show log details',
        previous: 'Previous',
        next: 'Next',
        pageStatus: 'Page {{page}} of {{lastPage}} · {{total}} entries',
        columns: {
          time: 'Time',
          level: 'Level',
          task: 'Task',
          message: 'Message',
        },
        empty: {
          title: 'No log entries',
          description: 'Log entries appear here once the background tasks start running.',
          filtered: 'Nothing has been logged by {{name}} yet.',
        },
        error: {
          title: 'Could not load logs',
          description: 'The log file is unavailable right now.',
        },
      },
    },
  },
  ru: {
    translation: {
      nav: {
        requests: 'Запросы',
        add: 'Добавить',
        system: 'Система',
        openMenu: 'Открыть меню навигации',
        languageLabel: 'Выберите язык',
        languages: {
          en: 'Английский',
          ru: 'Русский',
        },
      },
      common: {
        tryAgain: 'Повторить попытку',
        backToRequests: '← Назад к запросам',
        refresh: 'Обновить',
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
        queued: 'В очереди',
        running: 'Выполняется',
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
        filtersToggle: 'Фильтры',
        filtersToggleActive: 'Фильтры (активны)',
        refreshing: 'Обновляем данные…',
        filters: {
          typeLabel: 'Тип',
          statusLabel: 'Статус',
          active: 'В работе',
          all: 'Все',
          anyStatus: 'Любой',
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
          active: 'В работе',
          filtered: '{{label}}',
          withType: '{{status}} · {{type}}',
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
      discover: {
        title: 'Новый запрос',
        subtitle: 'Найдите в TVDB или TMDB и добавьте результат в Sonarr или Radarr',
        searchPlaceholder: 'Поиск фильмов и сериалов по названию…',
        actions: {
          add: 'Новый запрос',
          addShort: 'Добавить',
          search: 'Найти',
          request: 'Запросить',
          pickSeasons: 'Выбрать сезоны',
          viewRequest: 'Открыть запрос',
        },
        badges: {
          inLibrary: 'В библиотеке',
          requestedSeasons: 'Запрошено: {{seasons}}',
        },
        results: {
          heading: 'Результаты',
          count_one: '{{count}} результат',
          count_few: '{{count}} результата',
          count_many: '{{count}} результатов',
          count_other: '{{count}} результатов',
        },
        seasons: {
          label: 'Сезоны',
          season: 'Сезон {{season}}',
          specials: 'Спецэпизоды',
          selectAll: 'Выбрать все',
          clearAll: 'Снять все',
          alreadyRequested: 'Уже запрошен',
          alreadyDownloaded: 'Уже скачан полностью',
          sonarrWillFetch: 'Sonarr скачает его по мере выхода',
          allCovered:
            'Sonarr уже охватывает все сезоны этого сериала, поэтому выбрать можно только будущие сезоны.',
          newSeasons: 'Новые сезоны',
          newSeasonsHint: 'Запрашивать будущие сезоны этого сериала по мере их анонса.',
          none: 'У этого сериала пока нет доступных сезонов.',
          loadFailed: 'Не удалось загрузить сезоны этого сериала.',
        },
        modal: {
          rootFolder: 'Папка библиотеки',
          rootFolderHint: 'Куда Sonarr или Radarr сохранит файлы.',
          rootFolderPlaceholder: 'Выберите папку',
          rootFolderOption: '{{path}} (свободно {{free}})',
          rootFolderFailed: 'Не удалось загрузить доступные папки.',
          noRootFolders: 'В Sonarr или Radarr не настроено ни одной папки библиотеки.',
          inLibraryMovie: 'Фильм уже есть в Radarr, поэтому будет включено только отслеживание.',
          inLibrarySeries:
            'Сериал уже есть в Sonarr. Выбранный сезон добавится к тому, что отслеживает Sonarr; у остальных сезонов отслеживание не изменится.',
          confirm: 'Добавить запрос',
          confirmMonitoring: 'Сохранить отслеживание',
        },
        added_one: 'Добавлен {{count}} запрос',
        added_few: 'Добавлено {{count}} запроса',
        added_many: 'Добавлено {{count}} запросов',
        added_other: 'Добавлено {{count}} запросов',
        monitoringUpdated: 'Отслеживание обновлено',
        addFailed: 'Не удалось добавить запрос',
        empty: {
          title: 'Ничего не найдено',
          description: 'Попробуйте другое написание или оригинальное название.',
        },
        start: {
          title: 'Найдите то, что хотите запросить',
          description: 'Фильмы и сериалы ищутся вместе, поэтому не нужно знать заранее, что это.',
        },
        error: {
          title: 'Поиск не удался',
          description: 'Не удалось связаться с сервисом метаданных.',
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
      },
      releaseSearch: {
        placeholder: 'Поиск релизов для «{{title}}»…',
        ariaLabel: 'Поиск релизов для {{title}}',
        tabs: {
          search: 'Поиск',
          manual: 'Вручную',
        },
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
            age: 'Возраст',
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
          toggle: 'Фильтры',
          toggleActive: 'Фильтры (активны)',
          source: {
            label: 'Источник',
            all: 'Все источники',
          },
        },
        age: {
          unknown: 'Возраст неизвестен',
          today: 'Сегодня',
          days_one: '{{count}} день',
          days_few: '{{count}} дня',
          days_many: '{{count}} дней',
          days_other: '{{count}} дней',
        },
        empty: {
          title: 'Ничего не найдено',
          description: 'Измените поисковый запрос или попробуйте позже.',
        },
      },
      manualRelease: {
        instructions:
          'Релиз уже есть? Загрузите его .torrent-файл или вставьте magnet-ссылку — он сразу уйдёт в загрузчик.',
        or: 'или',
        file: {
          label: 'Torrent-файл',
          description:
            'Список файлов читается сразу, поэтому сопоставление проходит при добавлении.',
          placeholder: 'Выберите .torrent-файл',
          invalid: 'Это не .torrent-файл. Выберите сам торрент, а не медиафайл.',
        },
        magnet: {
          label: 'Magnet-ссылка',
          description: 'Имена файлов появятся, только когда загрузчик получит метаданные.',
          placeholder: 'magnet:?xt=urn:btih:…',
          invalid: 'Magnet-ссылка должна начинаться с «magnet:».',
        },
        actions: {
          submit: 'Добавить релиз',
          clear: 'Очистить',
        },
        toasts: {
          queuedTitle: 'Скачивание добавлено',
          queuedDescription: 'Релиз передан в загрузчик.',
          failedTitle: 'Не удалось добавить релиз',
          failedFallback: 'Ошибка при добавлении релиза',
        },
      },
      releaseCard: {
        source: 'Источник',
        progress: 'Прогресс',
        relatedRequests: 'Связанные запросы',
        added: 'Добавлен {{date}}',
        completed: 'Завершён {{date}}',
        stats: {
          seeders: 'Сиды',
          leechers: 'Личи',
          ratio: 'Рейтинг',
          health: 'Здоровье',
        },
        files: {
          total_one: '{{count}} файл',
          total_few: '{{count}} файла',
          total_many: '{{count}} файлов',
          video_one: '{{count}} видео',
          video_few: '{{count}} видео',
          video_many: '{{count}} видео',
          subtitle_one: '{{count}} субтитр',
          subtitle_few: '{{count}} субтитра',
          subtitle_many: '{{count}} субтитров',
        },
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
          remove: {
            title: 'Удалить запрос',
            description: 'Больше не отслеживать и снять мониторинг',
          },
        },
        seasons: {
          manage: 'Управление сезонами',
          modalTitle: 'Сезоны «{{title}}»',
          confirm: 'Сохранить сезоны',
          saved: 'Сезоны обновлены',
          saveFailed: 'Не удалось обновить сезоны',
          unavailable:
            'Sonarr ещё не связал этот запрос с сериалом, поэтому управлять его сезонами нельзя.',
          removeDialog: {
            title: 'Отключить отслеживание сезонов',
            body: 'Sonarr перестанет отслеживать {{seasons}}, а их запросы будут удалены. Уже скачанные файлы останутся на месте.',
            confirm: 'Отключить и сохранить',
          },
        },
        remove: {
          dialogTitle: 'Удалить запрос',
          dialogBodySeries:
            'Запрос будет удалён, а Sonarr перестанет отслеживать этот сезон. Сериал останется в библиотеке, как и уже скачанные файлы.',
          dialogBodyMovie:
            'Запрос будет удалён, а Radarr перестанет отслеживать этот фильм. Он останется в библиотеке, как и уже скачанные файлы.',
          confirm: 'Удалить запрос',
          removed: 'Запрос удалён',
          failed: 'Не удалось удалить запрос',
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
      tasks: {
        toasts: {
          queued: 'Синхронизация добавлена в очередь',
          finished: 'Синхронизация завершена',
          failedTitle: 'Ошибка синхронизации',
          failedFallback: 'Некоторые шаги синхронизации не завершились.',
          queueFailedTitle: 'Не удалось запустить синхронизацию',
          queueFailedFallback: 'Сервер отклонил запрос на синхронизацию.',
        },
        page: {
          title: 'Задачи',
          subtitle: 'Фоновые задачи Releasarr и история их запусков.',
          runAll: 'Запустить все',
          error: {
            title: 'Не удалось загрузить задачи',
            description: 'Список задач сейчас недоступен.',
          },
          stalled: {
            title: 'Задачи из очереди не выполняются',
            description: 'Задача ждёт слишком долго. Возможно, планировщик не запущен.',
          },
        },
        kinds: {
          sonarr_sync: {
            name: 'Синхронизация Sonarr',
            description: 'Загрузить нужные серии и сериалы из Sonarr.',
          },
          radarr_sync: {
            name: 'Синхронизация Radarr',
            description: 'Загрузить нужные фильмы из Radarr.',
          },
          release_sync: {
            name: 'Обновить загрузки',
            description: 'Обновить прогресс и состояние из клиента загрузок.',
          },
          export: {
            name: 'Импорт завершённых',
            description: 'Импортировать завершённые загрузки в Sonarr и Radarr.',
          },
          regrab: {
            name: 'Перезагрузка устаревших',
            description: 'Скачать заново релизы, заменённые на трекере.',
          },
        },
        triggers: {
          api: 'Вручную',
          download_client: 'Клиент загрузок',
          schedule: 'По расписанию',
        },
        scheduled: {
          title: 'Расписание',
          runNow: 'Запустить сейчас',
          runTask: 'Запустить «{{name}}» сейчас',
          never: 'Никогда',
          pendingFirstRun: 'При следующем старте',
          lastRunFailed: 'Последний запуск по расписанию завершился ошибкой.',
          columns: {
            name: 'Название',
            interval: 'Интервал',
            lastExecution: 'Последний запуск',
            lastDuration: 'Длительность',
            nextExecution: 'Следующий запуск',
          },
        },
        queue: {
          title: 'Очередь',
          description:
            'Запуски, инициированные вами или клиентом загрузок. Запуски по расписанию показаны выше.',
          count_one: '{{count}} запуск',
          count_few: '{{count}} запуска',
          count_many: '{{count}} запусков',
          active_one: '{{count}} активный',
          active_few: '{{count}} активных',
          active_many: '{{count}} активных',
          toggleDetails: 'Показать детали «{{name}}»',
          empty: {
            title: 'Пока нет запусков',
            description: 'Задачи, запущенные вручную, появятся здесь вместе с результатом.',
          },
          columns: {
            name: 'Название',
            trigger: 'Источник',
            queued: 'В очереди',
            started: 'Начало',
            duration: 'Длительность',
            status: 'Статус',
          },
        },
        output: {
          empty: 'Этот запуск не вернул подробностей.',
          errorTitle: 'Ошибка',
        },
      },
      logLevels: {
        info: 'Инфо',
        warning: 'Предупреждение',
        error: 'Ошибка',
      },
      taskLogs: {
        title: 'Логи',
        description: 'Всё, что записали фоновые задачи, сначала новые.',
        filterLabel: 'Фильтр по задаче',
        allTasks: 'Все задачи',
        source: 'Источник',
        toggleDetails: 'Показать подробности записи',
        previous: 'Назад',
        next: 'Вперёд',
        pageStatus: 'Страница {{page}} из {{lastPage}} · записей: {{total}}',
        columns: {
          time: 'Время',
          level: 'Уровень',
          task: 'Задача',
          message: 'Сообщение',
        },
        empty: {
          title: 'Записей нет',
          description: 'Записи появятся здесь после первого запуска фоновых задач.',
          filtered: 'Задача «{{name}}» пока ничего не записала.',
        },
        error: {
          title: 'Не удалось загрузить логи',
          description: 'Файл логов сейчас недоступен.',
        },
      },
    },
  },
} satisfies Resource;

export type AppLocale = keyof typeof resources;

export const supportedLocales = Object.keys(resources) as AppLocale[];
