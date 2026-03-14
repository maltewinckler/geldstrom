"""Health-check routes: liveness and readiness."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gateway.application.health.queries.evaluate_health import EvaluateHealthQuery

from ..dependencies import Factory
from ..schemas.health import LivenessResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LivenessResponse)
async def liveness(
    factory: Factory,
) -> LivenessResponse:
    result = await EvaluateHealthQuery.from_factory(factory).live()
    return LivenessResponse(status=result["status"])


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def readiness(
    factory: Factory,
) -> JSONResponse:
    result = await EvaluateHealthQuery.from_factory(factory).ready()
    body = ReadinessResponse(status=result["status"], checks=result["checks"])
    status_code = 200 if result["status"] == "ready" else 503
    return JSONResponse(content=body.model_dump(), status_code=status_code)
