"""Protocol-agnostic second-factor authentication challenges."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, PositiveFloat, model_validator


class TANConfig(BaseModel):
    """TAN polling configuration."""

    poll_interval: PositiveFloat = 2.0
    timeout_seconds: PositiveFloat = 120.0

    @model_validator(mode="after")
    def validate_config(self):
        if self.poll_interval > self.timeout_seconds:
            raise ValueError("poll_interval cannot exceed timeout_seconds")
        return self


class ChallengeType(Enum):
    TEXT = "text"
    MATRIX_CODE = "matrix_code"
    FLICKER = "flicker"
    PUSH = "push"
    DECOUPLED = "decoupled"
    PHOTO_TAN = "photo_tan"


class ChallengeData(BaseModel, frozen=True):
    """Binary data for visual challenges (matrix code, flicker, photo TAN)."""

    mime_type: str | None = None
    data: bytes


class Challenge(metaclass=ABCMeta):
    """Abstract base for protocol-agnostic 2FA challenges."""

    @property
    @abstractmethod
    def challenge_type(self) -> ChallengeType: ...

    @property
    @abstractmethod
    def challenge_text(self) -> str | None: ...

    @property
    @abstractmethod
    def challenge_html(self) -> str | None: ...

    @property
    @abstractmethod
    def challenge_data(self) -> ChallengeData | None: ...

    @property
    @abstractmethod
    def is_decoupled(self) -> bool: ...

    @abstractmethod
    def get_data(self) -> bytes: ...


@dataclass
class ChallengeResult:
    """Result of responding to a 2FA challenge."""

    response: str | None = None
    cancelled: bool = False
    error: str | None = None
    detach: bool = False

    @property
    def is_success(self) -> bool:
        return self.response is not None and not self.cancelled

    @property
    def needs_polling(self) -> bool:
        return self.response is None and not self.cancelled and not self.error


@runtime_checkable
class ChallengeHandler(Protocol):
    """Protocol for handling 2FA challenges across different UI environments."""

    def present_challenge(self, challenge: Challenge) -> ChallengeResult: ...


@runtime_checkable
class DecoupledPoller(Protocol):
    """Protocol for polling decoupled (app-based) authentication status."""

    def poll_status(
        self,
        challenge: Challenge,
        timeout_seconds: float = 120.0,
        poll_interval: float = 2.0,
    ) -> ChallengeResult: ...


class DecoupledTANPending(Exception):
    """Raised when a decoupled TAN challenge is detected and the caller opts out of internal polling."""

    def __init__(self, challenge: Challenge, task_reference: str) -> None:
        super().__init__(
            "Decoupled TAN challenge pending — caller must poll externally"
        )
        self.challenge = challenge
        self.task_reference = task_reference


class DetachingChallengeHandler:
    """ChallengeHandler that detaches on decoupled challenges instead of blocking."""

    def present_challenge(self, challenge: Challenge) -> ChallengeResult:
        if challenge.is_decoupled:
            return ChallengeResult(detach=True)
        raise ValueError(
            "Non-decoupled TAN challenges are not supported in detach mode"
        )


class InteractiveChallengeHandler:
    """Simple CLI challenge handler that prompts for TAN input."""

    def present_challenge(self, challenge: Challenge) -> ChallengeResult:
        if challenge.is_decoupled:
            print(f"Please confirm in your banking app: {challenge.challenge_text}")
            return ChallengeResult()  # needs_polling will be True

        if challenge.challenge_text:
            print(f"Challenge: {challenge.challenge_text}")

        if challenge.challenge_data:
            data = challenge.challenge_data
            if data.mime_type == "application/x-hhduc":
                print(f"Flicker code: {data.data.decode('us-ascii', errors='replace')}")
            else:
                print(f"Visual challenge ({data.mime_type}): {len(data.data)} bytes")

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
    "DecoupledTANPending",
    "DetachingChallengeHandler",
    "InteractiveChallengeHandler",
    "TANConfig",
]
