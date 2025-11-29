"""Decoupled TAN confirmation polling for FinTS."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable

from fints.domain.connection import (
    Challenge,
    ChallengeResult,
    DecoupledPoller,
)

logger = logging.getLogger(__name__)


@dataclass
class DecoupledPollingConfig:
    """Configuration for decoupled polling behavior."""

    poll_interval: float = 2.0  # Seconds between poll attempts
    timeout: float = 120.0  # Maximum time to wait
    max_attempts: int | None = None  # Max attempts (calculated from timeout if None)

    def __post_init__(self):
        if self.max_attempts is None:
            self.max_attempts = int(self.timeout / self.poll_interval)


# Type for the function that sends a poll request and returns result
PollFunction = Callable[[Challenge], tuple[bool, Challenge | object]]


class DecoupledConfirmationPoller(DecoupledPoller):
    """
    Polls for decoupled TAN confirmation.

    This handles the polling loop for decoupled authentication flows
    where the user confirms the transaction in their banking app.
    """

    def __init__(
        self,
        poll_function: PollFunction,
        config: DecoupledPollingConfig | None = None,
    ) -> None:
        """
        Initialize the poller.

        Args:
            poll_function: Function that sends a poll request and returns
                          (is_complete, result_or_new_challenge)
            config: Polling configuration
        """
        self._poll_function = poll_function
        self._config = config or DecoupledPollingConfig()

    def poll_status(
        self,
        challenge: Challenge,
        timeout_seconds: float | None = None,
        poll_interval: float | None = None,
    ) -> ChallengeResult:
        """
        Poll for decoupled confirmation.

        Args:
            challenge: The challenge to poll for
            timeout_seconds: Override timeout from config
            poll_interval: Override poll interval from config

        Returns:
            ChallengeResult with success, timeout, or error
        """
        timeout = timeout_seconds or self._config.timeout
        interval = poll_interval or self._config.poll_interval
        max_attempts = int(timeout / interval)

        current_challenge = challenge
        attempts = 0

        logger.info(
            "Starting decoupled polling (timeout=%ss, interval=%ss)",
            timeout,
            interval,
        )

        while attempts < max_attempts:
            if attempts > 0:
                time.sleep(interval)

            try:
                is_complete, result = self._poll_function(current_challenge)

                if is_complete:
                    logger.info("Decoupled confirmation received after %d attempts", attempts + 1)
                    return ChallengeResult(response="")  # Empty response for decoupled

                # Not complete - check if we got a new challenge to continue with
                if isinstance(result, Challenge):
                    current_challenge = result
                    logger.debug("Poll attempt %d: still waiting", attempts + 1)
                else:
                    # Got some other result, treat as completion
                    logger.info("Decoupled flow completed with result")
                    return ChallengeResult(response="")

            except Exception as e:
                logger.exception("Error during decoupled polling")
                return ChallengeResult(error=str(e))

            attempts += 1

        # Timeout
        logger.warning("Decoupled polling timed out after %d attempts", attempts)
        return ChallengeResult(
            error=f"Timed out waiting for decoupled confirmation after {timeout}s"
        )


__all__ = [
    "DecoupledConfirmationPoller",
    "DecoupledPollingConfig",
    "PollFunction",
]
