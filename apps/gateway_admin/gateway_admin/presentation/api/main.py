"""FastAPI application entry point for gateway-admin-ui."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gateway_admin.application.commands.initialize_admin import (
    InitializeDatabaseCommand,
)
from gateway_admin.application.commands.update_product_registration import (
    UpdateProductRegistrationCommand,
)
from gateway_admin.config import get_settings
from gateway_admin.infrastructure.persistence.sqlalchemy.factories.admin_factory import (
    AdminRepositoryFactorySQLAlchemy,
)
from gateway_admin.infrastructure.persistence.sqlalchemy.factories.service_factory import (
    ServiceFactorySQLAlchemy,
)

_default_frontend = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", str(_default_frontend)))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    repo_factory = AdminRepositoryFactorySQLAlchemy(settings=settings)
    service_factory = ServiceFactorySQLAlchemy.from_factory(repo_factory)

    await InitializeDatabaseCommand.from_factory(repo_factory)()
    await UpdateProductRegistrationCommand.from_factory(
        repo_factory,
        service_factory,
        product_version=settings.fints_product_version,
    )(settings.fints_product_registration_key)

    app.state.repo_factory = repo_factory
    app.state.service_factory = service_factory
    app.state.settings = settings
    yield
    await repo_factory.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gateway Admin API",
        description="Administrative API for managing gateway API consumers",
        version="1.0.0",
        lifespan=lifespan,
    )

    settings = get_settings()
    # The admin UI is only reachable via SSH port-forwarding.
    # Allow only the localhost origin that the browser uses after forwarding.
    allowed_origin = f"http://localhost:{settings.admin_ui_port}"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[allowed_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
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
