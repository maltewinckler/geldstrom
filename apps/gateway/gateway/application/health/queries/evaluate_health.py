"""Application-layer health evaluation for liveness and readiness."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Self

from ..ports.readiness_check import ReadinessCheck

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class EvaluateHealthQuery:
    """Centralize liveness and readiness evaluation for the backend."""

    def __init__(self, checks: Mapping[str, ReadinessCheck]) -> None:
        self._checks = dict(checks)

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(factory.readiness_checks)

    async def live(self) -> dict[str, str]:
        return {"status": "ok"}

    async def ready(self) -> dict[str, Any]:
        results: dict[str, str] = {}
        all_healthy = True

        for name, check in self._checks.items():
            try:
                healthy = await check()
            except Exception:
                healthy = False
            results[name] = "ok" if healthy else "failed"
            all_healthy = all_healthy and healthy

        return {
            "status": "ready" if all_healthy else "not_ready",
            "checks": results,
        }
