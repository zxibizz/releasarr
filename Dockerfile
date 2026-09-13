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
    apt-get -o Acquire::ForceIPv4=true install -y nginx curl xz-utils && \
    rm -rf /var/lib/apt/lists/*

# s6-overlay supervises the three processes this image runs. Extracted with
# curl rather than ADD because the arch-specific tarball name is only known
# after mapping TARGETARCH, which ADD cannot do.
ARG S6_OVERLAY_VERSION=3.2.3.2
ARG TARGETARCH
RUN set -eu; \
    case "${TARGETARCH:-}" in \
        amd64) s6_arch=x86_64 ;; \
        arm64) s6_arch=aarch64 ;; \
        *) echo "unsupported TARGETARCH: ${TARGETARCH:-unset}" >&2; exit 1 ;; \
    esac; \
    release="https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}"; \
    curl -fsSL "${release}/s6-overlay-noarch.tar.xz" | tar -C / -Jxpf -; \
    curl -fsSL "${release}/s6-overlay-${s6_arch}.tar.xz" | tar -C / -Jxpf -

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

# The nginx site, the migration step, and the three supervised services, each
# already at the path it occupies in the image
COPY docker/root/ /
RUN chmod +x /etc/cont-init.d/* /etc/services.d/*/run /etc/services.d/*/log/run

# Abort the boot if migrations fail instead of serving against a stale schema.
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2
# Docker allows 10s before SIGKILL; leave uvicorn most of it to drain the
# request it is holding, which for an indexer search can be seconds.
ENV S6_SERVICES_GRACETIME=8000

EXPOSE 80

ENTRYPOINT ["/init"]
