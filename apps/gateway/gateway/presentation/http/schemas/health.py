"""Health endpoint schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str


class ReadinessResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    checks: dict[str, Any]
