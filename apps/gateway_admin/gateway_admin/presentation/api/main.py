"""FastAPI application entry point for gateway-admin-ui."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gateway_admin.application.commands.update_product_registration import (
    UpdateProductRegistrationCommand,
)
from gateway_admin.config import get_settings
from gateway_admin.infrastructure.persistence.sqlalchemy.db_init import (
    initialize_database,
)
from gateway_admin.infrastructure.persistence.sqlalchemy.factories.admin_factory import (
    AdminRepositoryFactorySQLAlchemy,
)
from gateway_admin.infrastructure.persistence.sqlalchemy.factories.service_factory import (
    ServiceFactorySQLAlchemy,
)

logger = logging.getLogger(__name__)

_default_frontend = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", str(_default_frontend)))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    # Ensure schema and DB user exist (idempotent).
    await initialize_database(settings)

    repo_factory = AdminRepositoryFactorySQLAlchemy(settings=settings)
    service_factory = ServiceFactorySQLAlchemy.from_factory(repo_factory)

    # Seed the product registration from settings (idempotent - upserts).
    await UpdateProductRegistrationCommand.from_factory(
        repo_factory,
        service_factory,
        product_version=settings.fints_product_version,
    )(settings.fints_product_registration_key)
    logger.info("Product registration seeded.")

    app.state.repo_factory = repo_factory
    app.state.service_factory = service_factory
    yield
    await repo_factory.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gateway Admin API",
        description="Administrative API for managing gateway API consumers",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .routes import router

    app.include_router(router, prefix="/admin")

    if FRONTEND_DIR.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(FRONTEND_DIR / "assets")),
            name="assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> FileResponse:
            index_path = FRONTEND_DIR / "index.html"
            if not index_path.exists():
                raise HTTPException(status_code=404, detail="Frontend not built")
            return FileResponse(index_path)

    return app


app = create_app()
