"""PendingChallenge entity — aggregate root for the 2FA challenge lifecycle."""

from __future__ import annotations

from pydantic import BaseModel

from gateway.domain.banking.value_objects.connection import BankingProtocol
from gateway.domain.session.value_objects.session_identity import SessionIdentity


# Entity / Aggregate Root — identified by SessionIdentity.session_id
class PendingChallenge(BaseModel, frozen=True):
    """A parked 2FA challenge waiting for a TAN response.

    Entity / Aggregate Root:
      - Identified by identity.session_id
      - Has a TTL lifecycle (SESSION_TTL_SECONDS) managed by ChallengeRepository
      - dialog_state carries opaque serialized banking session bytes
      - Never stores credentials (zero-knowledge design)
    """

    identity: SessionIdentity
    protocol: BankingProtocol
    bank_code: str  # Needed to look up endpoint during resume
    dialog_state: bytes
    challenge_type: str
    challenge_text: str | None = None
    media_data: bytes | None = None
