"""FinTS Informational Segments.

These segments are returned by some banks but are not essential for core operations.
They contain informational data about authorization schemes, visualization, etc.

Since the exact structure can vary between banks, these are implemented with
flexible field handling that accepts any data.
"""
from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from ..base import FinTSSegment, FinTSDataElementGroup
from ..types import (
    FinTSAlphanumeric,
    FinTSCode,
    FinTSNumeric,
)


# =============================================================================
# Supporting DEGs
# =============================================================================


class AuthorizationSecurityScheme(FinTSDataElementGroup):
    """Authorization Security Scheme information.

    This DEG contains information about the authorization security scheme
    supported by the bank. The exact fields may vary between banks.

    Source: FinTS 3.0 Sicherheitsverfahren
    """

    # Common fields - all optional since structure varies
    security_scheme_code: FinTSCode | None = Field(
        default=None,
        description="Sicherheitsverfahren Code",
    )
    security_scheme_name: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=30,
        description="Name des Sicherheitsverfahrens",
    )
    security_scheme_version: FinTSNumeric | None = Field(
        default=None,
        description="Version des Sicherheitsverfahrens",
    )


class VisualizationInfo(FinTSDataElementGroup):
    """Visualization information.

    This DEG contains information about how to visualize certain
    elements to the user. The exact fields may vary between banks.

    Source: FinTS 3.0 Sicherheitsverfahren
    """

    # Common fields - all optional since structure varies
    visualization_type: FinTSCode | None = Field(
        default=None,
        description="Art der Visualisierung",
    )
    visualization_text: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=256,
        description="Visualisierungstext",
    )


# =============================================================================
# Informational Segments
# =============================================================================


class HIAZSS1(FinTSSegment):
    """Authorization Security Scheme Segment, version 1.

    This segment contains information about the authorization security
    schemes supported by the bank. It is informational only.

    Note: The exact structure varies significantly between banks.
    This implementation accepts any data to ensure parsing doesn't fail
    on bank-specific variations.

    Source: FinTS 3.0 Sicherheitsverfahren
    """

    SEGMENT_TYPE: ClassVar[str] = "HIAZSS"
    SEGMENT_VERSION: ClassVar[int] = 1

    # Use flexible alphanumeric fields that accept any data
    # Banks send varying structures, so we accept anything
    max_number_tasks: FinTSAlphanumeric | None = Field(
        default=None,
        description="Maximale Anzahl Aufträge oder allg. Parameter",
    )
    min_number_signatures: FinTSAlphanumeric | None = Field(
        default=None,
        description="Anzahl Signaturen mindestens oder allg. Parameter",
    )
    security_class: FinTSAlphanumeric | None = Field(
        default=None,
        description="Sicherheitsklasse oder allg. Parameter",
    )
    # Extra data captured as a catch-all for remaining fields
    extra_data: list[Any] | None = Field(
        default=None,
        description="Additional unstructured data",
    )


class HIVISS1(FinTSSegment):
    """Visualization Information Segment, version 1.

    This segment contains visualization information for the user interface.
    It is informational only.

    Note: The exact structure varies significantly between banks.
    This implementation accepts any data to ensure parsing doesn't fail
    on bank-specific variations.

    Source: FinTS 3.0 Sicherheitsverfahren
    """

    SEGMENT_TYPE: ClassVar[str] = "HIVISS"
    SEGMENT_VERSION: ClassVar[int] = 1

    # Use flexible alphanumeric fields that accept any data
    # Banks send varying structures, so we accept anything
    max_number_tasks: FinTSAlphanumeric | None = Field(
        default=None,
        description="Maximale Anzahl Aufträge oder allg. Parameter",
    )
    min_number_signatures: FinTSAlphanumeric | None = Field(
        default=None,
        description="Anzahl Signaturen mindestens oder allg. Parameter",
    )
    security_class: FinTSAlphanumeric | None = Field(
        default=None,
        description="Sicherheitsklasse oder allg. Parameter",
    )
    # Extra data captured as a catch-all for remaining fields
    extra_data: list[Any] | None = Field(
        default=None,
        description="Additional unstructured data",
    )


# =============================================================================
# Version Registries
# =============================================================================


HIAZSS_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HIAZSS1,
}

HIVISS_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HIVISS1,
}


__all__ = [
    # DEGs
    "AuthorizationSecurityScheme",
    "VisualizationInfo",
    # Segments
    "HIAZSS1",
    "HIVISS1",
    # Registries
    "HIAZSS_VERSIONS",
    "HIVISS_VERSIONS",
]

