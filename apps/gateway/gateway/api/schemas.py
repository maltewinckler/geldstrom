"""Request/response schemas for the Gateway API layer.

These are Pydantic models for HTTP serialization. Credential fields use plain
strings here — conversion to SecretStr happens at the domain boundary.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Union

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Shared sub-schemas
# ---------------------------------------------------------------------------


class BankConnectionSchema(BaseModel):
    protocol: str
    bank_code: str
    username: str
    pin: str


class DateRangeSchema(BaseModel):
    start: date
    end: date


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class InitialFetchRequest(BaseModel):
    bank_connection: BankConnectionSchema
    iban: str
    date_range: DateRangeSchema


class ResumeFetchRequest(BaseModel):
    session_id: str
    tan_response: str


# Pydantic resolves the correct variant by matching fields (left-to-right).
FetchTransactionsRequest = Union[InitialFetchRequest, ResumeFetchRequest]


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TransactionSchema(BaseModel):
    entry_id: str
    booking_date: date
    value_date: date
    amount: Decimal
    currency: str
    purpose: str
    counterpart_name: str | None = None
    counterpart_iban: str | None = None
    metadata: dict[str, str] = {}


class ChallengeSchema(BaseModel):
    session_id: str
    type: str
    media_data: bytes | None = None


class FetchTransactionsResponse(BaseModel):
    status: str  # "success" | "challenge_required"
    transactions: list[TransactionSchema] | None = None
    challenge: ChallengeSchema | None = None


class VersionResponse(BaseModel):
    git_commit_hash: str
    docker_image_sha256: str


# ---------------------------------------------------------------------------
# Error schemas
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail
