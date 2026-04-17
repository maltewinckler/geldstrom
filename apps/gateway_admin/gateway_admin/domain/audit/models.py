"""Audit domain value objects."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class AuditEventType(StrEnum):
    CONSUMER_AUTHENTICATED = "consumer_authenticated"
    CONSUMER_AUTH_FAILED = "consumer_auth_failed"
    TOKEN_REROLLED = "token_rerolled"


class AuditEvent(BaseModel, frozen=True):
    event_id: UUID
    event_type: AuditEventType
    consumer_id: UUID | None  # None for unknown-key auth failures
    occurred_at: datetime  # always UTC


class AuditQuery(BaseModel, frozen=True):
    consumer_id: UUID | None = None
    event_type: AuditEventType | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    page: int = 1
    page_size: int = 50


class AuditPage(BaseModel, frozen=True):
    events: list[AuditEvent]
    total: int
    page: int
    page_size: int
