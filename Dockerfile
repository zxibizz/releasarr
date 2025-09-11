FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# ------------------------------------------------

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS backend-builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --group db-migrations

# ------------------------------------------------

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y nginx && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=backend-builder --chown=app:app /app/.venv /app/.venv
COPY --from=frontend-builder --chown=app:app /app/build /static

COPY backend/src /app/src
COPY backend/migrations /app/migrations
COPY backend/alembic.ini /app

COPY nginx.conf /etc/nginx/sites-available/default
COPY entrypoint.sh /

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
