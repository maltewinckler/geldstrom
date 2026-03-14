"""FastAPI application factory with lifespan management."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from gateway import lifecycle
from gateway.application.common import ApplicationError

from .middleware.cache_control import CacheControlMiddleware
from .middleware.exception_handlers import application_error_handler
from .middleware.request_id import RequestIDMiddleware
from .routers import accounts, health, operations, tan_methods, transactions

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
    app = FastAPI(
        title="Banking Gateway API",
        version="1.0.0",
        lifespan=_lifespan,
    )

    # Middleware (registered last = outermost wrap)
    app.add_middleware(CacheControlMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Exception handlers
    app.add_exception_handler(ApplicationError, application_error_handler)

    # Routers
    app.include_router(health.router)
    app.include_router(accounts.router)
    app.include_router(transactions.router)
    app.include_router(tan_methods.router)
    app.include_router(operations.router)

    return app
