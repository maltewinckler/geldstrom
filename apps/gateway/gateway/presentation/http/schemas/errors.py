"""Shared error response schema."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error envelope returned for all 4xx/5xx responses."""

    model_config = {"extra": "forbid"}

    error: str
    message: str
