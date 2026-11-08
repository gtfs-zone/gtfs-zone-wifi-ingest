# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---

FROM python:3.13-slim-bookworm

WORKDIR /app

# Same ids as the Deployment's securityContext.
RUN groupadd -g 10001 ingest && useradd -u 10001 -g ingest -M ingest

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY schemas/ /app/schemas/

ENV PATH="/app/.venv/bin:$PATH" \
    SCHEMA_DIR=/app/schemas

USER ingest

EXPOSE 8000

CMD ["gtfs-zone-wifi-ingest"]
