"""Health-check routes: liveness and readiness."""

from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import JSONResponse

from gateway.application.common import GetReadinessQuery
from gateway.presentation.http.dependencies import Factory
from gateway.presentation.http.schemas.health import (
    LivenessResponse,
    ReadinessCheck,
    ReadinessResponse,
)

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(factory: Factory) -> JSONResponse:
    status = await GetReadinessQuery.from_factory(factory)()
    body = ReadinessResponse(
        status="ready" if status.is_ready else "not_ready",
        checks=ReadinessCheck(
            db="ok" if status.db else "error",
            product_key="loaded" if status.product_key else "missing",
            catalog="ok" if status.catalog else "empty",
            redis="ok" if status.redis else "error",
        ),
    )
    return JSONResponse(
        status_code=200 if status.is_ready else 503,
        content=body.model_dump(),
    )
