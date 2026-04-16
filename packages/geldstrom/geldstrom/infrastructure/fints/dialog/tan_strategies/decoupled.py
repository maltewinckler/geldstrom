"""Decoupled TAN strategy - app-based approval via response code 3955.

When the bank returns code 3955, the user must approve the operation in their
banking app. The challenge_handler receives the challenge and must return
detach=True, which raises DecoupledTANPending so the caller can poll
externally via Dialog.poll_decoupled_once() (used by FinTS3ClientDecoupled).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from geldstrom.infrastructure.fints.challenge import DecoupledTANPending
from geldstrom.infrastructure.fints.dialog.challenge import FinTSChallenge

from .base import (
    find_highest_hitans,
    get_hktan_class,
    inject_hktan_for_business_segments,
)

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.challenge import ChallengeHandler
    from geldstrom.infrastructure.fints.dialog.responses import ProcessedResponse
    from geldstrom.infrastructure.fints.protocol import ParameterStore

    from .base import SendTANCallback

logger = logging.getLogger(__name__)


class DecoupledTanStrategy:
    """HKTAN injection + decoupled (app-based) TAN approval handling."""

    def __init__(
        self,
        security_function: str,
    ) -> None:
        self._security_function = security_function

    @property
    def is_two_step(self) -> bool:
        return True

    @property
    def security_function(self) -> str:
        return self._security_function

    def prepare_segments(
        self,
        segments: list,
        parameters: ParameterStore,
    ) -> list:
        return inject_hktan_for_business_segments(segments, parameters)

    def handle_response(
        self,
        response: ProcessedResponse,
        challenge_handler: ChallengeHandler | None,
        send_tan_callback: SendTANCallback | None = None,
    ) -> ProcessedResponse | None:
        if not response.get_response_by_code("3955"):
            return None

        logger.info("Decoupled TAN required - waiting for app approval...")
        return self._handle_decoupled(
            response,
            challenge_handler,
            send_tan_callback,
        )

    def _handle_decoupled(
        self,
        init_response: ProcessedResponse,
        challenge_handler: ChallengeHandler | None,
        send_tan_callback: SendTANCallback | None,
    ) -> ProcessedResponse | None:
        hitan = init_response.find_segment_first("HITAN")
        if not hitan:
            logger.warning("No HITAN segment in response, cannot poll for approval")
            return None
        task_ref = getattr(hitan, "task_reference", None)
        if not task_ref:
            logger.warning("No task_reference in HITAN, cannot poll for approval")
            return None

        if challenge_handler is not None:
            challenge = FinTSChallenge(hitan, is_decoupled=True)
            result = challenge_handler.present_challenge(challenge)
            if result.cancelled:
                raise ValueError("User cancelled the TAN challenge")
            if result.error:
                raise ValueError(f"Challenge handler error: {result.error}")
            if result.detach:
                raise DecoupledTANPending(challenge=challenge, task_reference=task_ref)

        logger.warning(
            "No challenge_handler provided for decoupled TAN - cannot obtain approval"
        )
        return None


def build_status_hktan(bpd_segments: Any, task_reference: str) -> Any | None:
    """Build an HKTAN status query segment (tan_process='S')."""
    hitans = find_highest_hitans(bpd_segments)
    if not hitans:
        raise ValueError("No HITANS in BPD, cannot build status HKTAN")

    hktan_class, _ = get_hktan_class(hitans.header.version)
    if not hktan_class:
        raise ValueError("No supported HKTAN version found for polling")

    status_hktan = hktan_class(tan_process="S")
    if hasattr(status_hktan, "task_reference"):
        status_hktan.task_reference = task_reference
    if hasattr(status_hktan, "further_tan_follows"):
        status_hktan.further_tan_follows = False
    return status_hktan
