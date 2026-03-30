"""Result DTO for the get-tan-methods command."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from gateway.domain.banking_gateway import OperationStatus, TanMethod


@dataclass(frozen=True)
class TanMethodsResultEnvelope:
    """Application result for TAN-method discovery requests."""

    status: OperationStatus
    methods: list[TanMethod] = field(default_factory=list)
    operation_id: str | None = None
    expires_at: datetime | None = None
    failure_reason: str | None = None
