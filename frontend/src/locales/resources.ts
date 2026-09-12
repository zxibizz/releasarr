import type { Resource } from 'i18next';

export const defaultNS = 'translation';

export const resources = {
  en: {
    translation: {
      nav: {
        requests: 'Requests',
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
        instructions:
          'Enter a title or identifier and press the search button to fetch release candidates.',
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
          source: {
            label: 'Source',
            all: 'All sources',
          },
        },
        quality: {
          unknown: 'Unknown',
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
          release_sync: {
            name: 'Refresh Downloads',
            description: 'Update download progress and state from the download client.',
          },
          export: {
            name: 'Import Finished',
            description: 'Import completed downloads into Sonarr.',
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
        instructions:
          'Введите название или идентификатор и нажмите поиск, чтобы получить кандидатов.',
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
          source: {
            label: 'Источник',
            all: 'Все источники',
          },
        },
        quality: {
          unknown: 'Неизвестно',
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
          release_sync: {
            name: 'Обновить загрузки',
            description: 'Обновить прогресс и состояние из клиента загрузок.',
          },
          export: {
            name: 'Импорт завершённых',
            description: 'Импортировать завершённые загрузки в Sonarr.',
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
