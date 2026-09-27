# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
