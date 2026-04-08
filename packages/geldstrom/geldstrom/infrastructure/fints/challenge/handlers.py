"""Challenge handler protocols and implementations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import Challenge, ChallengeResult


@runtime_checkable
class ChallengeHandler(Protocol):
    """Protocol for handling 2FA challenges across different UI environments."""

    def present_challenge(self, challenge: Challenge) -> ChallengeResult: ...


class DetachingChallengeHandler:
    """ChallengeHandler that detaches on decoupled challenges instead of blocking."""

    def present_challenge(self, challenge: Challenge) -> ChallengeResult:
        if challenge.is_decoupled:
            return ChallengeResult(detach=True)
        raise ValueError("Non-decoupled TAN challenges are not supported")
