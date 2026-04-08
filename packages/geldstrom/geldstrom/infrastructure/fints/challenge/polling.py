"""Decoupled TAN polling and configuration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, PositiveFloat, model_validator

from .types import Challenge


class TANConfig(BaseModel):
    """TAN polling configuration."""

    poll_interval: PositiveFloat = 2.0
    timeout_seconds: PositiveFloat = 120.0

    @model_validator(mode="after")
    def validate_config(self):
        if self.poll_interval > self.timeout_seconds:
            raise ValueError("poll_interval cannot exceed timeout_seconds")
        return self


class DecoupledTANPending(Exception):
    """Raised when a decoupled TAN challenge is detected and the caller opts out of internal polling."""

    def __init__(
        self,
        challenge: Challenge,
        task_reference: str,
        context: Any = None,
    ) -> None:
        super().__init__(
            "Decoupled TAN challenge pending — caller must poll externally"
        )
        self.challenge = challenge
        self.task_reference = task_reference
        self.context = context
