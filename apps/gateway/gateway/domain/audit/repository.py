"""Audit domain repository protocol (write port)."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.audit.models import AuditEvent


class AuditRepository(Protocol):
    async def append(self, event: AuditEvent) -> None: ...
