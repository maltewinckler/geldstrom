"""Internal exceptions used by the Geldstrom anti-corruption layer."""

from __future__ import annotations

from datetime import datetime

from geldstrom.infrastructure.fints.session import FinTSSessionState


class GeldstromPendingConfirmation(Exception):
    """Signals that the bank requires a later decoupled confirmation poll."""

    def __init__(self, session_state: FinTSSessionState, expires_at: datetime) -> None:
        super().__init__("Banking operation is pending external confirmation")
        self.session_state = session_state
        self.expires_at = expires_at
