"""Domain objects for statement archives."""
from __future__ import annotations

from datetime import date
from typing import Mapping

from pydantic import BaseModel


class StatementReference(BaseModel, frozen=True):
    """Describes an addressable statement artifact for an account."""

    account_id: str
    statement_id: str
    period_start: date | None = None
    period_end: date | None = None
    issued_on: date | None = None
    metadata: Mapping[str, str] = {}


class StatementDocument(BaseModel, frozen=True):
    """Binary representation of a statement in a negotiated format."""

    reference: StatementReference
    content: bytes
    content_type: str
    metadata: Mapping[str, str] = {}
