"""Port for the gateway readiness service."""

from __future__ import annotations

from typing import Protocol

from gateway.application.common.readiness import ReadinessStatus


class GatewayReadinessPort(Protocol):
    """Check whether the gateway's backing infrastructure is operational."""

    async def check(self) -> ReadinessStatus: ...
