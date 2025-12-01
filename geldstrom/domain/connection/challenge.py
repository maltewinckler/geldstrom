"""Protocol-agnostic second-factor authentication challenges."""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class ChallengeType(Enum):
    """
    Types of second-factor authentication challenges.

    These are protocol-agnostic categories that cover common 2FA methods
    across different banking protocols (FinTS, PSD2, EBICS, etc.).
    """

    TEXT = "text"  # Simple text challenge (e.g., "Enter TAN from letter")
    MATRIX_CODE = "matrix_code"  # QR code or matrix image to scan
    FLICKER = "flicker"  # Optical flicker code for TAN generators (chipTAN)
    PUSH = "push"  # Push notification to mobile app
    DECOUPLED = "decoupled"  # Confirmation in separate channel (app, device)
    PHOTO_TAN = "photo_tan"  # Photo/image-based TAN (similar to matrix but colored)


class ChallengeData(BaseModel, frozen=True):
    """
    Binary or structured data associated with a challenge.

    For matrix codes, flicker codes, or photo TANs, this holds the
    raw data needed to render or transmit the challenge.
    """

    mime_type: str | None = None  # e.g., "image/png" for matrix codes
    data: bytes  # Raw challenge data


class Challenge(metaclass=ABCMeta):
    """
    Abstract base for second-factor authentication challenges.

    This represents the protocol-agnostic concept of a 2FA challenge
    that requires user interaction before a banking operation can proceed.

    Concrete implementations (e.g., FinTS NeedTANResponse) add
    protocol-specific details and serialization.
    """

    @property
    @abstractmethod
    def challenge_type(self) -> ChallengeType:
        """The type of challenge presented to the user."""

    @property
    @abstractmethod
    def challenge_text(self) -> str | None:
        """Human-readable challenge text to display."""

    @property
    @abstractmethod
    def challenge_html(self) -> str | None:
        """HTML-formatted challenge text (if available)."""

    @property
    @abstractmethod
    def challenge_data(self) -> ChallengeData | None:
        """Binary data for visual challenges (QR, flicker, photo)."""

    @property
    @abstractmethod
    def is_decoupled(self) -> bool:
        """Whether this challenge uses a decoupled confirmation flow."""

    @abstractmethod
    def get_data(self) -> bytes:
        """Serialize this challenge for later resumption."""


@dataclass
class ChallengeResult:
    """
    Result of presenting a challenge to the user.

    Attributes:
        response: The user's response (e.g., TAN code), or None for decoupled
        cancelled: True if the user cancelled the challenge
        error: Error message if something went wrong
    """

    response: str | None = None
    cancelled: bool = False
    error: str | None = None

    @property
    def is_success(self) -> bool:
        """Return True if user provided a response."""
        return self.response is not None and not self.cancelled

    @property
    def needs_polling(self) -> bool:
        """Return True if this requires decoupled polling."""
        return self.response is None and not self.cancelled and not self.error


@runtime_checkable
class ChallengeHandler(Protocol):
    """
    Protocol for handling 2FA challenges.

    Implementations of this protocol are responsible for presenting
    challenges to users and collecting their responses. This allows
    different UI implementations (CLI, GUI, web) to handle challenges
    appropriately.

    Example implementations:
    - Interactive CLI that prompts for TAN input
    - GUI dialog showing QR codes or flicker animations
    - Web handler that returns challenge data to frontend
    - Automated handler for decoupled flows (just waits)
    """

    def present_challenge(self, challenge: Challenge) -> ChallengeResult:
        """
        Present a challenge to the user and collect their response.

        For interactive challenges (TEXT, MATRIX_CODE, FLICKER, PHOTO_TAN),
        this should display the challenge and wait for user input.

        For DECOUPLED and PUSH challenges, this may return immediately
        with needs_polling=True, indicating that poll_decoupled should
        be called to wait for confirmation.

        Args:
            challenge: The challenge to present

        Returns:
            ChallengeResult with user's response or status
        """


@runtime_checkable
class DecoupledPoller(Protocol):
    """
    Protocol for polling decoupled authentication status.

    Decoupled authentication (e.g., app-based confirmation) requires
    periodic polling to check if the user has confirmed the operation
    in their banking app.
    """

    def poll_status(
        self,
        challenge: Challenge,
        timeout_seconds: float = 120.0,
        poll_interval: float = 2.0,
    ) -> ChallengeResult:
        """
        Poll for decoupled authentication confirmation.

        This method should periodically check if the user has confirmed
        the operation in their banking app, until either:
        - Confirmation is received (return success)
        - Timeout is reached (return error)
        - User cancels (return cancelled)

        Args:
            challenge: The decoupled challenge to poll for
            timeout_seconds: Maximum time to wait for confirmation
            poll_interval: Seconds between poll attempts

        Returns:
            ChallengeResult indicating success, timeout, or cancellation
        """


class InteractiveChallengeHandler:
    """
    Simple interactive challenge handler for CLI applications.

    This handler prints challenge information and prompts for TAN input.
    For decoupled challenges, it returns immediately with needs_polling=True.
    """

    def present_challenge(self, challenge: Challenge) -> ChallengeResult:
        """Present challenge and collect response interactively."""
        if challenge.is_decoupled:
            # Decoupled challenges need polling, not direct input
            print(f"Please confirm in your banking app: {challenge.challenge_text}")
            return ChallengeResult()  # needs_polling will be True

        # Display challenge info
        if challenge.challenge_text:
            print(f"Challenge: {challenge.challenge_text}")

        if challenge.challenge_data:
            data = challenge.challenge_data
            if data.mime_type == "application/x-hhduc":
                print(f"Flicker code: {data.data.decode('us-ascii', errors='replace')}")
            else:
                print(f"Visual challenge ({data.mime_type}): {len(data.data)} bytes")

        # Prompt for TAN
        try:
            tan = input("Enter TAN: ").strip()
            if not tan:
                return ChallengeResult(cancelled=True)
            return ChallengeResult(response=tan)
        except (KeyboardInterrupt, EOFError):
            return ChallengeResult(cancelled=True)


__all__ = [
    "Challenge",
    "ChallengeData",
    "ChallengeHandler",
    "ChallengeResult",
    "ChallengeType",
    "DecoupledPoller",
    "InteractiveChallengeHandler",
]
