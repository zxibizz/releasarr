# Alembic Migrations

This directory contains database migrations for the Releasarr backend.

## Setup

Alembic is already configured in this project. The configuration is in `alembic.ini` and the migration environment is in `migrations/env.py`.

## Creating a New Migration

To create a new migration, run:

```bash
cd backend_new
alembic revision --autogenerate -m "Description of the migration"
```

This will create a new migration file in the `migrations/versions` directory.

## Running Migrations

To run all pending migrations:

```bash
cd backend_new
alembic upgrade head
```

To run migrations up to a specific revision:

```bash
cd backend_new
alembic upgrade <revision>
```

## Downgrading Migrations

To downgrade to a previous revision:

```bash
cd backend_new
alembic downgrade <revision>
```

To downgrade one revision:

```bash
cd backend_new
alembic downgrade -1
```

## Checking Migration Status

To see the current revision:

```bash
cd backend_new
alembic current
```

To see migration history:

```bash
cd backend_new
alembic history
```

## Database Connection

The database connection string is configured in `app/settings.py`. By default, it uses:

```
postgresql+asyncpg://postgres:postgres@localhost:5432/releasarr
```

You can override this by setting the `DB_CONNECTION_STRING` environment variable.
