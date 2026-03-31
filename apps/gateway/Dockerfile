# syntax=docker/dockerfile:1
# Build context: repository root

# =============================================================================
# Stage 1 - Build
# =============================================================================
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

COPY uv.lock pyproject.toml ./
COPY packages/geldstrom/         packages/geldstrom/
COPY packages/gateway-contracts/ packages/gateway-contracts/
COPY apps/gateway/               apps/gateway/

RUN uv sync --frozen --no-dev --no-editable --no-install-workspace --package gateway


# =============================================================================
# Stage 2 - Runtime
# =============================================================================
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system gateway && \
    useradd --system --no-create-home --gid gateway gateway

WORKDIR /app

COPY --from=builder --chown=gateway:gateway /build/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

USER gateway

CMD ["gateway-server"]
