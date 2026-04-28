"""Audit domain repository protocol (read port)."""

from __future__ import annotations

from typing import Protocol

from gateway_admin.domain.audit.models import AuditPage, AuditQuery


class AuditQueryRepository(Protocol):
    async def query(self, q: AuditQuery) -> AuditPage: ...
