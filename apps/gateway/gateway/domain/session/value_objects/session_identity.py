"""SessionIdentity value object."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

SESSION_TTL_SECONDS = 300


def _make_session_identity() -> SessionIdentity:
    return SessionIdentity(
        session_id=uuid.uuid4().hex,
        expires_at=datetime.now(UTC) + timedelta(seconds=SESSION_TTL_SECONDS),
    )


# Value Object — identity by session_id
class SessionIdentity(BaseModel, frozen=True):
    """Identifies a parked challenge session.

    Value Object: equality by session_id + expires_at.
    The session_id is a UUID4 hex string (128-bit entropy).
    """

    session_id: str  # UUID4 hex, 128-bit entropy
    expires_at: datetime

    @staticmethod
    def create() -> SessionIdentity:
        """Factory: generate a new session with UUID4 hex id and 300s expiry."""
        return _make_session_identity()
