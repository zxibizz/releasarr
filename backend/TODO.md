Usecases 

1. Заходим на главную, видим незамэтченные фильмы и шоу
2. Заходим внутрь, видим на разных вкладках
- Список сезонов и серий и их мэтчи
- Список релизов и их мэтчи
3. Можем делать поиск нового релиза
- после выбора релиза файлы автоматически мэтчатся к сезонам и сериям
- мэтчи можно править руками
4. После окончания скачивания делаем импорт в sonarr / radarr
5. При выходе новой серии в wanted/missing периодически производится поиск обновлений сматченного с сезоном релиза
- при наличии обновления автоматически обновляем релиз
- если из релиза были убраны старые файлы то кидаем ошибку
- если новые файлы не удается смэтчить автоматически кидаем уведомление


Pages

Запросы
Сериалы (?)
Фильмы (?)
Календарь (?)
Релизы (?)

Tables

Searches
    pk=Series/Show id
    data=prowlarr response
Releases
    pk=Qbittorrent name
    data=
        Stats
        season matching
        file matching
TVDB
    pk=tvdbId
    data=tvdb data