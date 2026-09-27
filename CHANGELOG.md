# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **URL base.** Set **Settings → General → URL base** (or `RELEASARR_URL_BASE`) to, say,
  `/releasarr` and restart, and the whole app — UI, API, installed PWA — is served under that
  path, as the \*arr apps' own URL Base setting does.
- **`?apikey=` authenticates like `X-Api-Key`**, as in the \*arr apps, for tools that can only
  be given a URL. nginx logs it as `(removed)`.
- **`GET /ping`**, unauthenticated, answers `{"status": "OK"}` while the database does — the
  probe uptime monitors already use for Sonarr and Radarr.

### Changed

- **Sonarr, Radarr, Prowlarr and qBittorrent are configured by their own address**, e.g.
  `http://sonarr:8989`, with no `/api/v3` suffix — Releasarr appends the API path. A URL that
  still ends in the old suffix keeps working.
- **The API moved to `/api/v1`.** `GET /api/system` is now `GET /api/v1/system/status` and also
  reports `app_name` and `url_base`. Scripts calling the API need the new prefix.
- **`/api/healthz` and `/api/readyz` are replaced by `/ping`.** The container healthcheck
  follows; update any external monitor that polled them.
- **The refresh cookie now lives at `<url base>/api/v1/auth`**, so everyone signs in once more
  after upgrading. The `RELEASARR_AUTH_COOKIE_PATH` setting is gone; the path follows the URL
  base.

## [0.11.0] - 2026-09-27

The first release with a published image. v0.10.0 was tagged, but its image was never built
and the tag has been withdrawn, so everything listed under it arrives here.

### Added

- **TheTVDB and TMDB are credited** on the Add Request page and in the README, as TMDB's API
  terms require.
- **The README lists what Releasarr talks to and what it does not do**: supported API
  versions, torrents through qBittorrent only, and no URL base.

### Fixed

- **Pausing and resuming works on qBittorrent 5**, which renamed those endpoints to stop and
  start. Adding a torrent paused is honoured there too. qBittorrent 4.x keeps working.

### Changed

- **`Dockerfile.all-in-one` is now `Dockerfile`**, so `docker build .` builds the production
  image. Only matters if you build it yourself.
- **The image runs Python 3.14** (was 3.12), and the frontend is built on Node 26.
  Dependencies are updated to match.
- **The compose examples no longer require `ARR_NETWORK`** or assume the \*arr apps are
  containers on the same host. Existing `compose.yaml` files keep working as they are.

### Removed

- **`POST /api/tasks/sync_downloads`.** The release sync already queues the import as soon as
  it sees a torrent finish, so a qBittorrent completion hook adds nothing. Remove any hook that
  calls it.

## 0.10.0 - 2026-09-26 [YANKED]

First public release.

### Added

- **Published image**: `ghcr.io/zxibizz/releasarr`, for `linux/amd64` and
  `linux/arm64`, with compose examples for a single container on SQLite and for
  a split web/worker deployment on Postgres.
- **`/config` volume with `PUID`/`PGID`**: the database, logs and the generated
  auth secret all live under `/config`, owned by the configured user.
- **`RELEASARR_AUTH_SECRET` is generated on first start** into
  `/config/auth-secret` when not set.
- **`RELEASARR_MODE`** runs the container as `all` (the default), `web` or
  `worker`.
- **Version reporting**: `GET /api/healthz` and the new `GET /api/system` report
  the running version, and the System area shows it.
- **Container healthcheck.**

### Changed

- **The container listens on 8050**, not 80.
- **`RELEASARR_AUTH_COOKIE_SECURE` defaults to `false`**, so logging in works
  over plain HTTP on a LAN. Set it to `true` behind TLS.
- **`RELEASARR_METADATA_LANGUAGES` defaults to English only.**

See [docs/upgrading.md](docs/upgrading.md) for moving an existing install onto
the new layout.

[Unreleased]: https://github.com/zxibizz/releasarr/compare/v0.11.0...HEAD
[0.11.0]: https://github.com/zxibizz/releasarr/releases/tag/v0.11.0
