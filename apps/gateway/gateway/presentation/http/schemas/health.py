"""Health endpoint schemas."""

from __future__ import annotations

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str


class ReadinessCheck(BaseModel):
    model_config = {"extra": "forbid"}

    db: str
    product_key: str
    catalog: str
    redis: str


class ReadinessResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    checks: ReadinessCheck
