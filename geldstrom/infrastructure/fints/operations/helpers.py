"""Helper functions for FinTS operations.

This module provides helpers for:
- Accessing segment fields and metadata
- Version negotiation between client and bank
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from geldstrom.exceptions import FinTSUnsupportedOperation

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount


def get_account_type_for_segment(segment_class: type[Any]) -> type[Any] | None:
    """Get the account field type for a segment class.

    Args:
        segment_class: The segment class to inspect

    Returns:
        The type of the 'account' field, or None if not found

    Example:
        account_type = get_account_type_for_segment(HKSAL6)
        account = account_type.from_sepa_account(sepa_account)
    """
    if hasattr(segment_class, "model_fields"):
        account_field = segment_class.model_fields.get("account")
        if account_field:
            return account_field.annotation
    return None


def build_account_field(segment_class: type[Any], account: "SEPAAccount") -> Any:
    """Build an account field for a segment from a SEPAAccount.

    This combines get_account_type_for_segment() and from_sepa_account()
    into a single call for convenience.

    Args:
        segment_class: The segment class (e.g., HKSAL6, HKKAZ7)
        account: The SEPAAccount to convert

    Returns:
        Account field instance suitable for the segment

    Raises:
        ValueError: If segment has no account field or conversion fails
    """
    account_type = get_account_type_for_segment(segment_class)
    if account_type is None:
        raise ValueError(f"Segment {segment_class.__name__} has no account field")
    return account_type.from_sepa_account(account)


def get_segment_version(segment_class: type[Any]) -> int:
    """Get the version number from a segment class.

    Args:
        segment_class: The segment class to inspect

    Returns:
        The segment version number
    """
    if hasattr(segment_class, "SEGMENT_VERSION"):
        return segment_class.SEGMENT_VERSION
    return getattr(segment_class, "VERSION", 0)


def get_segment_type(segment_class: type[Any]) -> str:
    """Get the type string from a segment class.

    Args:
        segment_class: The segment class to inspect

    Returns:
        The segment type string (e.g., "HKSAL", "HKKAZ")
    """
    if hasattr(segment_class, "SEGMENT_TYPE"):
        return segment_class.SEGMENT_TYPE
    return getattr(segment_class, "TYPE", "")


def find_highest_supported_version(
    bpd_segments,
    segment_classes: Sequence[type],
    *,
    raise_if_missing: str | None = None,
) -> type | None:
    """
    Find the highest version of a segment supported by both bank and client.

    Args:
        bpd_segments: BPD segments from ParameterStore
        segment_classes: Segment classes the client supports (e.g., HKSAL5, HKSAL6)
        raise_if_missing: If provided, raise FinTSUnsupportedOperation with this
            message if no supported version is found

    Returns:
        Highest supported segment class, or None if not supported

    Raises:
        FinTSUnsupportedOperation: If raise_if_missing is set and no version found
    """
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

