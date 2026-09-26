# syntax=docker/dockerfile:1
#
# One image, three shapes, picked at runtime by RELEASARR_MODE (s6-overlay supervises):
#   all    - nginx on :8050 serving the SPA and proxying the API, uvicorn, scheduler
#   web    - nginx + uvicorn only; queues jobs, never runs them
#   worker - the scheduler only; serves nothing
# web and worker meet at the sync_jobs table, so apart they need a shared database.

FROM node:26-slim AS frontend-builder
WORKDIR /app
COPY services/frontend/package.json services/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY services/frontend/ .
ENV VITE_API_URL=/api
RUN npm run build

# ------------------------------------------------

FROM ghcr.io/astral-sh/uv:0.12 AS uv

# Must be the exact image the runtime stage uses: the venv is bound to the
# interpreter that built it.
FROM python:3.14-slim-bookworm AS backend-builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=services/backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=services/backend/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# ------------------------------------------------

FROM python:3.14-slim-bookworm

# tzdata makes TZ work, as it does in the *arr images.
RUN apt-get -o Acquire::ForceIPv4=true update && \
    apt-get -o Acquire::ForceIPv4=true install -y --no-install-recommends \
        ca-certificates curl nginx tzdata xz-utils && \
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
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --from=backend-builder /app/.venv /app/.venv
COPY --from=frontend-builder /app/dist /static
COPY services/backend/src /app/src
COPY services/backend/alembic /app/alembic
COPY services/backend/alembic.ini /app

# The nginx site, the init steps, and the three supervised services, each
# already at the path it occupies in the image
COPY cicd/containers/prod/root/ /
RUN chmod +x /etc/cont-init.d/* /etc/services.d/*/run /etc/services.d/*/log/run \
        /usr/local/bin/releasarr-healthcheck

# Fail the build, not the container, if the venv does not match the interpreter.
RUN python -c "import src.api.app, src.tasks.scheduler_service, asyncpg, aiosqlite"

ENV PUID=1000 \
    PGID=1000 \
    RELEASARR_MODE=all \
    RELEASARR_DATABASE_URL=sqlite+aiosqlite:////config/releasarr.db \
    RELEASARR_LOG_FILE=/config/logs/backend.log \
    RELEASARR_SCHEDULER_LOG_FILE=/config/logs/scheduler.log

# Abort the boot if migrations fail instead of serving against a stale schema.
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2
# Docker allows 10s before SIGKILL; leave uvicorn most of it to drain the
# request it is holding, which for an indexer search can be seconds.
ENV S6_SERVICES_GRACETIME=8000
ENV S6_KILL_GRACETIME=1000

VOLUME ["/config"]
# Nothing listens in worker mode; there the check asks s6 about the scheduler.
EXPOSE 8050

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["/usr/local/bin/releasarr-healthcheck"]

ENTRYPOINT ["/init"]
