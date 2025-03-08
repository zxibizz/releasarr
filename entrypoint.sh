#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting Nginx in daemon mode..."
nginx

echo "Starting Uvicorn..."
exec uvicorn src.app:app
