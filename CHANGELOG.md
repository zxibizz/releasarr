# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **`Dockerfile.all-in-one` is now `Dockerfile`**, so `docker build .` builds the production
  image. Only matters if you build it yourself.

## [0.10.0] - 2026-09-26

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

[Unreleased]: https://github.com/zxibizz/releasarr/compare/v0.10.0...HEAD
[0.10.0]: https://github.com/zxibizz/releasarr/releases/tag/v0.10.0
