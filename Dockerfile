FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
ENV VITE_API_URL=/api
RUN npm run build

# ------------------------------------------------

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS backend-builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# ------------------------------------------------

FROM python:3.12-slim-bookworm

# Install Nginx
RUN apt-get -o Acquire::ForceIPv4=true update && \
    apt-get -o Acquire::ForceIPv4=true install -y nginx curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

# Copy Environment
COPY --from=backend-builder --chown=app:app /app/.venv /app/.venv

# Copy Frontend
COPY --from=frontend-builder --chown=app:app /app/dist /static

# Copy Backend Code
COPY backend/src /app/src
COPY backend/alembic /app/alembic
COPY backend/alembic.ini /app

# Configure Nginx
COPY nginx.conf /etc/nginx/sites-available/default

# Setup Entrypoint
COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
