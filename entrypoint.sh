#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting Nginx in daemon mode..."
nginx

echo "Starting Scheduler Service..."
python -m src.tasks.scheduler_service &

echo "Starting Uvicorn..."
exec uvicorn src.api.app:app --host 0.0.0.0 --port 8000
