# syntax=docker/dockerfile:1
# Build context: repository root

# =============================================================================
# Stage 1 - Frontend build
# =============================================================================
FROM node:24-slim AS frontend-builder

WORKDIR /frontend

COPY apps/gateway_admin/frontend/package.json \
     apps/gateway_admin/frontend/package-lock.json* \
     apps/gateway_admin/frontend/vite.config.js \
     ./

RUN npm ci --prefer-offline

COPY apps/gateway_admin/frontend/ ./

RUN npm run build


# =============================================================================
# Stage 2 - Python build
# =============================================================================
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /build

COPY uv.lock pyproject.toml ./
COPY packages/gateway-contracts/ packages/gateway-contracts/
COPY apps/gateway_admin/     apps/gateway_admin/

RUN uv sync --frozen --no-dev --no-editable --package gateway-admin


# =============================================================================
# Stage 3 - Runtime
# =============================================================================
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system gw-admin && \
    useradd --system --no-create-home --gid gw-admin gw-admin

WORKDIR /app

COPY --from=builder --chown=gw-admin:gw-admin /app/.venv /app/.venv
COPY --from=frontend-builder --chown=gw-admin:gw-admin /frontend/dist /app/frontend

ENV PATH="/app/.venv/bin:$PATH" \
    FRONTEND_DIR="/app/frontend"

USER gw-admin

EXPOSE 8000

CMD ["uvicorn", "gateway_admin.presentation.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]
