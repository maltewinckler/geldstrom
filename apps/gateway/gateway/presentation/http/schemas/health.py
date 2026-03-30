"""Health endpoint schemas."""

from __future__ import annotations

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
