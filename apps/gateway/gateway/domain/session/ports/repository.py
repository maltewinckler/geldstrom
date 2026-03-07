"""ChallengeRepository port.

Kept close to the session domain it serves: stores and retrieves PendingChallenge.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gateway.domain.session.entities.pending_challenge import PendingChallenge
from gateway.domain.session.value_objects.session_identity import SessionIdentity


@runtime_checkable
class ChallengeRepository(Protocol):
    """Ephemeral storage for parked banking dialog state."""

    async def save(self, challenge: PendingChallenge) -> None: ...

    async def get(self, session_id: SessionIdentity) -> PendingChallenge | None: ...

    async def delete(self, session_id: SessionIdentity) -> None: ...
