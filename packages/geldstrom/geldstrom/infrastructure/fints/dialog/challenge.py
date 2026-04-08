"""FinTS-specific Challenge implementation bridging HITAN segments to domain interface."""

from __future__ import annotations

from typing import Any

from geldstrom.infrastructure.fints.challenge import (
    Challenge,
    ChallengeData,
    ChallengeType,
)


class FinTSChallenge(Challenge):
    """
    FinTS-specific challenge wrapping HITAN segment data.

    This implementation extracts challenge information from HITAN segments
    returned by the bank when decoupled TAN approval is required.

    Attributes:
        _hitan: The raw HITAN segment from the bank response
        _challenge_text: Human-readable challenge text
        _challenge_data: Optional binary data for visual challenges
        _is_decoupled: Whether this is a decoupled (app-based) challenge
    """

    def __init__(self, hitan: Any, *, is_decoupled: bool | None = None) -> None:
        self._hitan = hitan
        self._task_reference = getattr(hitan, "task_reference", None)

        # Extract challenge text
        self._challenge_text = getattr(hitan, "challenge", None)

        # Extract HHD_UC data for visual challenges
        hhduc_data = getattr(hitan, "challenge_hhduc", None)
        if hhduc_data:
            self._challenge_data = ChallengeData(
                mime_type="application/x-hhduc",
                data=hhduc_data
                if isinstance(hhduc_data, bytes)
                else hhduc_data.encode(),
            )
        else:
            self._challenge_data = None

        # Decoupled TAN: no direct user input needed, just app confirmation.
        # Use explicit flag if provided (from TAN strategy), else heuristic.
        if is_decoupled is not None:
            self._is_decoupled = is_decoupled
        else:
            self._is_decoupled = self._task_reference is not None and hhduc_data is None

    @property
    def challenge_type(self) -> ChallengeType:
        """The type of challenge presented to the user."""
        if self._is_decoupled:
            return ChallengeType.DECOUPLED
        return ChallengeType.TEXT

    @property
    def challenge_text(self) -> str | None:
        """Human-readable challenge text to display."""
        return self._challenge_text

    @property
    def challenge_html(self) -> str | None:
        """HTML-formatted challenge text (not supported in FinTS)."""
        return None

    @property
    def challenge_data(self) -> ChallengeData | None:
        """Binary data for visual challenges."""
        return self._challenge_data

    @property
    def is_decoupled(self) -> bool:
        """Whether this challenge uses a decoupled confirmation flow."""
        return self._is_decoupled

    @property
    def task_reference(self) -> str | None:
        """The task reference for status polling."""
        return self._task_reference

    def get_data(self) -> bytes:
        """Serialize this challenge for later resumption."""
        # For now, just serialize the task reference
        ref = self._task_reference or ""
        return ref.encode("utf-8")


__all__ = ["FinTSChallenge"]
