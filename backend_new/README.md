# Releasarr Backend (FastAPI)

This service implements the HTTP API consumed by the new React frontend. It is built with FastAPI, SQLAlchemy 2.0, and async HTTP clients that integrate with Sonarr, TVDB, Prowlarr, and qBittorrent.

## Features

- CRUD endpoints for media requests (`/requests`)
- Release management (`/releases`, `/releases/stats`)
- Torrent search and download orchestration (`/torrents`)
- Background scheduler that synchronises missing Sonarr series, imports qBittorrent
  statistics, exports completed releases back to Sonarr, and re-grabs outdated
  releases using Prowlarr
- External service clients (Sonarr, TVDB, Prowlarr, qBittorrent) with opt-in configuration
- SQLite (default) or any SQLAlchemy-supported database via configuration

## Quick start

```bash
cd backend_new
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Environment variables map directly to the field names in `app/core/config.py`. For example:

```bash
export DATABASE_URL="sqlite+aiosqlite:///./db.sqlite3"
export PROWLARR_URL="http://localhost:9696"
export PROWLARR_API_KEY="changeme"
export QBITTORRENT_URL="http://localhost:8080"
export QBITTORRENT_USERNAME="admin"
export QBITTORRENT_PASSWORD="adminadmin"
```

## Database initialisation

First apply the migrations:

```bash
uv run alembic upgrade head
```

Optional: load demo data for local testing:

```bash
uv run python -m app.db.init_db
```

## External services

All integrations are optional. When credentials are missing, the backend gracefully skips outbound calls (for example torrent downloads or Sonarr synchronisation). Provide the corresponding environment variables to enable them.

## Project layout

- `app/main.py` – FastAPI application factory
- `app/models/` – SQLAlchemy ORM models
- `app/schemas/` – Pydantic response/request models aligned with the frontend OpenAPI spec
- `app/services/` – Business logic coordinating persistence and external services
- `app/clients/` – Async HTTP clients for Sonarr, TVDB, Prowlarr, qBittorrent
- `app/api/routes/` – Route handlers grouped by domain
- `app/db/` – Database configuration and helpers
