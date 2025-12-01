"""Payment initiation port."""
from __future__ import annotations

from typing import Protocol

from geldstrom.domain import PaymentConfirmation, PaymentInstruction, SessionToken


class PaymentPort(Protocol):
    """Submit payment instructions through the active session."""

    def submit_single_transfer(
        self,
        state: SessionToken,
        instruction: PaymentInstruction,
    ) -> PaymentConfirmation:
        raise NotImplementedError
