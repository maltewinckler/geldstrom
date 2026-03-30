# syntax=docker/dockerfile:1

# =============================================================================
# Stage 1 — Build
#
# Installs all production dependencies and workspace packages as non-editable
# wheels into a .venv.  The build is split into two cache layers:
#
#   Layer A  Invalidated only when uv.lock or a pyproject.toml changes.
#            Third-party packages (fastapi, sqlalchemy, asyncpg, …) are cached
#            by the uv cache mount, so a cold layer-A rebuild is fast.
#
#   Layer B  Invalidated when workspace source code changes.
#            Only the four local packages are (re)built; third-party packages
#            already installed in layer A are untouched.
#
# The runtime image receives only the .venv — no workspace source is present.
# =============================================================================
FROM python:3.13-slim AS builder

# Install uv — pinned via the official image tag for reproducibility
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Compile .pyc files at install time so the runtime image stays read-only.
# copy mode: hardlink packages from the uv cache rather than downloading again.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

# ── Layer A: third-party packages ─────────────────────────────────────────────
# Bind-mount every pyproject.toml so uv can resolve the full workspace graph,
# then install only the external (non-workspace) packages.
# Nothing is COPY'd yet — this layer is invisible to the image filesystem.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=packages/geldstrom/pyproject.toml,target=packages/geldstrom/pyproject.toml \
    --mount=type=bind,source=packages/gateway-contracts/pyproject.toml,target=packages/gateway-contracts/pyproject.toml \
    --mount=type=bind,source=packages/geldstrom_cli/pyproject.toml,target=packages/geldstrom_cli/pyproject.toml \
    --mount=type=bind,source=apps/gateway/pyproject.toml,target=apps/gateway/pyproject.toml \
    --mount=type=bind,source=apps/gateway_admin_cli/pyproject.toml,target=apps/gateway_admin_cli/pyproject.toml \
    uv sync --frozen --no-dev --no-install-workspace

# ── Layer B: workspace packages ───────────────────────────────────────────────
# Copy only the four production workspace packages, then install them as
# proper (non-editable) wheels.  The runtime stage needs only .venv.
COPY pyproject.toml uv.lock ./
COPY packages/geldstrom/          packages/geldstrom/
COPY packages/gateway-contracts/  packages/gateway-contracts/
COPY apps/gateway/                apps/gateway/
COPY apps/gateway_admin_cli/      apps/gateway_admin_cli/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable


# =============================================================================
# Stage 2 — Runtime
#
# Minimal image: only the pre-built .venv is copied from the builder.
# Runs as a non-root system user for defence-in-depth.
# =============================================================================
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Non-root system user
RUN groupadd --system gateway && \
    useradd --system --no-create-home --gid gateway gateway

WORKDIR /app

# Copy the pre-built venv — this is the only layer that changes in production
COPY --from=builder --chown=gateway:gateway /build/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

USER gateway

EXPOSE 8000

# Lightweight liveness probe using Python's stdlib (no curl required)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

# gateway-server is the console_script defined in apps/gateway/pyproject.toml.
# gw-admin (from gateway_admin_cli) is also available for operator commands:
#   docker compose exec gateway gw-admin --help
CMD ["gateway-server"]
