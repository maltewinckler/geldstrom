"""Helper functions for FinTS operations."""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from geldstrom.infrastructure.fints.exceptions import FinTSUnsupportedOperation

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount


def get_account_type_for_segment(segment_class: type[Any]) -> type[Any] | None:
    """Get the account field type for a segment class."""
    if hasattr(segment_class, "model_fields"):
        account_field = segment_class.model_fields.get("account")
        if account_field:
            return account_field.annotation
    return None


def build_account_field(segment_class: type[Any], account: "SEPAAccount") -> Any:
    """Build an account field for a segment from a SEPAAccount."""
    account_type = get_account_type_for_segment(segment_class)
    if account_type is None:
        raise ValueError(f"Segment {segment_class.__name__} has no account field")
    return account_type.from_sepa_account(account)


def get_segment_version(segment_class: type[Any]) -> int:
    """Get the version number from a segment class."""
    if hasattr(segment_class, "SEGMENT_VERSION"):
        return segment_class.SEGMENT_VERSION
    return getattr(segment_class, "VERSION", 0)


def get_segment_type(segment_class: type[Any]) -> str:
    """Get the type string from a segment class."""
    if hasattr(segment_class, "SEGMENT_TYPE"):
        return segment_class.SEGMENT_TYPE
    return getattr(segment_class, "TYPE", "")


def find_highest_supported_version(
    bpd_segments,
    segment_classes: Sequence[type],
    *,
    raise_if_missing: str | None = None,
) -> type | None:
    """Find the highest version of a segment supported by both bank and client."""
    # Build version map
    version_map = {get_segment_version(cls): cls for cls in segment_classes}

    # Build parameter segment name (HKSAL -> HISALS)
    first_class = segment_classes[0]
    param_name = f"HI{get_segment_type(first_class)[2:]}S"

    # Find highest version in BPD that we also support
    highest = None
    for seg in bpd_segments.find_segments(param_name):
        version = seg.header.version
        is_higher = highest is None or version > highest.header.version
        if version in version_map and is_higher:
            highest = seg

    if not highest:
        if raise_if_missing:
            raise FinTSUnsupportedOperation(raise_if_missing)
        return None

    return version_map.get(highest.header.version)
