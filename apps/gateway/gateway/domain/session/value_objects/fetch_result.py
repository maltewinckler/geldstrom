"""Fetch result value objects — output of a banking fetch or TAN resume."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel

from gateway.domain.banking.value_objects.transaction import TransactionData

if TYPE_CHECKING:
    from gateway.domain.session.entities.pending_challenge import PendingChallenge


class FetchStatus(StrEnum):
    SUCCESS = "success"
    CHALLENGE_REQUIRED = "challenge_required"


# Value Object — API-facing projection of PendingChallenge
class ChallengeInfo(BaseModel, frozen=True):
    """Subset of PendingChallenge safe to return to the API caller.

    Value Object: immutable projection, no lifecycle.
    """

    session_id: str
    type: str
    media_data: bytes | None = None


# Value Object — output of a fetch or resume operation
class FetchResult(BaseModel, frozen=True):
    """Result of a BankingClient.fetch_transactions or resume_with_tan call.

    Value Object: immutable, produced by the infrastructure adapter.
    pending_challenge is set by the adapter when status == CHALLENGE_REQUIRED
    so the use case can persist it without knowing protocol internals.
    """

    model_config = {"arbitrary_types_allowed": True}

    status: FetchStatus
    transactions: list[TransactionData] | None = None
    challenge: ChallengeInfo | None = None
    pending_challenge: PendingChallenge | None = None
