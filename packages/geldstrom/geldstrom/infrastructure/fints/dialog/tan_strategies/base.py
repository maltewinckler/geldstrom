"""TANStrategy protocol and shared HKTAN helper functions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from geldstrom.infrastructure.fints.protocol import HKTAN_VERSIONS

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.challenge import ChallengeHandler
    from geldstrom.infrastructure.fints.dialog.responses import ProcessedResponse
    from geldstrom.infrastructure.fints.protocol import ParameterStore

logger = logging.getLogger(__name__)

# Segments that should NOT have HKTAN added (dialog management only).
DIALOG_SEGMENTS = {"HKIDN", "HKVVB", "HKEND", "HKSYN", "HKTAN"}


@runtime_checkable
class TANStrategy(Protocol):
    """Strategy for handling TAN authentication during FinTS dialog communication.

    Two implementations:
    - NoTanStrategy: security_function=999, no HKTAN injection
    - DecoupledTanStrategy: HKTAN injected, bank returns 3955 for app approval
    """

    @property
    def is_two_step(self) -> bool: ...

    @property
    def security_function(self) -> str: ...

    def prepare_segments(
        self,
        segments: list,
        parameters: ParameterStore,
    ) -> list:
        """Prepare segments for sending - optionally inject HKTAN."""
        ...

    def handle_response(
        self,
        response: ProcessedResponse,
        challenge_handler: ChallengeHandler | None,
        send_tan_callback: SendTANCallback | None = None,
    ) -> ProcessedResponse | None:
        """Handle response after sending - TAN processing if needed.

        Returns a replacement ProcessedResponse if TAN handling produced a
        final response, or None if the original response should be used as-is.
        """
        ...


class SendTANCallback(Protocol):
    """Callback for sending HKTAN segments (used by strategies to poll/submit)."""

    def __call__(self, segments: list) -> ProcessedResponse: ...


# ---------------------------------------------------------------------------
# Shared HKTAN utilities
# ---------------------------------------------------------------------------


def find_highest_hitans(bpd_segments: Any) -> Any | None:
    """Find the highest-version HITANS segment in BPD."""
    hitans = None
    for seg in bpd_segments.find_segments("HITANS"):
        if hitans is None or seg.header.version > hitans.header.version:
            hitans = seg
    return hitans


def get_hktan_class(hitans_version: int) -> tuple[type | None, int]:
    """Get the HKTAN class for the given HITANS version, with fallback."""
    hktan_class = HKTAN_VERSIONS.get(hitans_version)
    if hktan_class:
        return hktan_class, hitans_version
    for v in sorted(HKTAN_VERSIONS.keys(), reverse=True):
        if v <= hitans_version:
            return HKTAN_VERSIONS[v], v
    return None, 0


def segment_requires_tan(parameters: ParameterStore, segment_type: str) -> bool:
    """Check HIPINS in BPD to determine if a segment requires TAN."""
    from geldstrom.infrastructure.fints.protocol import HIPINS1

    hipins = parameters.bpd.segments.find_segment_first(HIPINS1)
    if not hipins:
        logger.debug("No HIPINS in BPD, assuming TAN required for %s", segment_type)
        return True

    if hasattr(hipins, "parameter") and hasattr(
        hipins.parameter, "transaction_tans_required"
    ):
        for req in hipins.parameter.transaction_tans_required:
            if req.transaction == segment_type:
                return req.tan_required

    logger.debug(
        "Segment %s not in HIPINS transaction list, assuming TAN required",
        segment_type,
    )
    return True


def build_hktan_for_segment(
    parameters: ParameterStore, segment_type: str
) -> Any | None:
    """Build an HKTAN segment for a business segment (tan_process='4')."""
    hitans = find_highest_hitans(parameters.bpd.segments)
    if not hitans:
        logger.warning("No HITANS in BPD, cannot build HKTAN")
        return None

    hktan_class, hktan_version = get_hktan_class(hitans.header.version)
    if not hktan_class:
        logger.warning("No supported HKTAN version found")
        return None

    hktan = hktan_class(tan_process="4")
    if hktan_version >= 6 and hasattr(hktan, "segment_type"):
        hktan.segment_type = segment_type
    return hktan


def inject_hktan_for_business_segments(
    segments: list,
    parameters: ParameterStore,
) -> list:
    """Inject HKTAN after each business segment that requires TAN per HIPINS."""
    result = []
    for seg in segments:
        result.append(seg)

        seg_type = getattr(seg.header, "type", None) if hasattr(seg, "header") else None
        if (
            seg_type
            and seg_type not in DIALOG_SEGMENTS
            and segment_requires_tan(parameters, seg_type)
        ):
            hktan = build_hktan_for_segment(parameters, seg_type)
            if hktan:
                logger.debug("Injecting HKTAN for %s operation", seg_type)
                result.append(hktan)

    return result
