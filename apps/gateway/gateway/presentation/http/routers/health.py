"""Health-check routes: liveness and readiness."""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas.health import LivenessResponse

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")
