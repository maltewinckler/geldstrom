"""FastAPI application factory with lifespan management."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from gateway.application.common import ApplicationError
from gateway.presentation.http import lifecycle

from .middleware.cache_control import CacheControlMiddleware
from .middleware.exception_handlers import application_error_handler
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.request_id import RequestIDMiddleware
from .routers import accounts, balances, health, operations, tan_methods, transactions

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    await lifecycle.startup()
    resume_task = asyncio.create_task(lifecycle.run_resume_worker())
    try:
        yield
    finally:
        resume_task.cancel()
        with suppress(asyncio.CancelledError):
            await resume_task
        await lifecycle.shutdown()


def create_app() -> FastAPI:
    """Construct and configure the gateway FastAPI application."""
    import os

    from gateway.presentation.http.dependencies import get_settings

    settings = get_settings()

    workers = int(os.getenv("GATEWAY_WORKERS", "1"))
    if workers > 1 and settings.rate_limit_requests_per_minute > 0:
        logger.warning(
            "RateLimitMiddleware uses in-process state — rate limits are NOT "
            "shared across %d workers. Set GATEWAY_WORKERS=1 or replace the "
            "middleware with a shared store (e.g. Redis).",
            workers,
        )

    app = FastAPI(
        title="Banking Gateway API",
        version="1.0.0",
        lifespan=_lifespan,
    )

    # Middleware (registered last = outermost wrap)
    app.add_middleware(CacheControlMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_requests_per_minute,
    )

    # Exception handlers
    app.add_exception_handler(ApplicationError, application_error_handler)

    # Routers
    app.include_router(health.router)
    app.include_router(accounts.router)
    app.include_router(balances.router)
    app.include_router(transactions.router)
    app.include_router(tan_methods.router)
    app.include_router(operations.router)

    return app
