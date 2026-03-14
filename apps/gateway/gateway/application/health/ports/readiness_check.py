"""Readiness check protocol for health evaluation."""

from __future__ import annotations

from typing import Protocol


class ReadinessCheck(Protocol):
    """Async check used by readiness evaluation."""

    async def __call__(self) -> bool: ...
