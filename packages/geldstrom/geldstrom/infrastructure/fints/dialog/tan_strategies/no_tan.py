"""No-TAN strategy - pass-through for security_function=999.

Used for anonymous dialogs, sync dialogs, and banks that don't require TAN
for basic operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.challenge import ChallengeHandler
    from geldstrom.infrastructure.fints.dialog.responses import ProcessedResponse
    from geldstrom.infrastructure.fints.protocol import ParameterStore

    from .base import SendTANCallback


class NoTanStrategy:
    """No TAN handling - segments pass through unmodified, responses returned as-is."""

    @property
    def is_two_step(self) -> bool:
        return False

    @property
    def security_function(self) -> str:
        return "999"

    def prepare_segments(
        self,
        segments: list,
        parameters: ParameterStore,
    ) -> list:
        return segments

    def handle_response(
        self,
        response: ProcessedResponse,
        challenge_handler: ChallengeHandler | None,
        send_tan_callback: SendTANCallback | None = None,
    ) -> ProcessedResponse | None:
        return None
