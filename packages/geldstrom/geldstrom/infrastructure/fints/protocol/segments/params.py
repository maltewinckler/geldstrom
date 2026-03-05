"""FinTS Parameter Segments.

Parameter segments (ending in 'S') contain configuration information
for various operations. Most follow a standard structure:
- header
- max_number_tasks
- min_number_signatures
- security_class
- parameter (operation-specific DEG)

However, some bank-specific segments have non-standard structures.
We provide both:
1. Standard parameter segments for known structures
2. Generic segments that capture any data flexibly
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from ..base import FinTSDataElementGroup, FinTSSegment
from ..types import (
    FinTSAlphanumeric,
    FinTSBool,
    FinTSNumeric,
)

# =============================================================================
# Base Classes for Parameter Segments
# =============================================================================


class ParameterSegmentBase(FinTSSegment):
    """Base class for parameter segments.

    Standard parameter segments have these fields before
    their operation-specific parameter DEG.
    """

    max_number_tasks: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=1000,
        description="Maximale Anzahl Aufträge",
    )
    min_number_signatures: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10,
        description="Anzahl Signaturen mindestens",
    )
    security_class: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10,
        description="Sicherheitsklasse",
    )


class GenericParameter(FinTSDataElementGroup):
    """Generic parameter DEG that accepts any data.

    Used for bank-specific parameter segments where the exact
    structure is unknown or varies between banks.
    """

    # Flexible fields that accept any data
    field1: FinTSAlphanumeric | None = Field(default=None)
    field2: FinTSAlphanumeric | None = Field(default=None)
    field3: FinTSAlphanumeric | None = Field(default=None)
    field4: FinTSAlphanumeric | None = Field(default=None)
    field5: FinTSAlphanumeric | None = Field(default=None)
    field6: FinTSAlphanumeric | None = Field(default=None)
    field7: FinTSAlphanumeric | None = Field(default=None)
    field8: FinTSAlphanumeric | None = Field(default=None)


# =============================================================================
# Generic Segment for Unknown/Variable Structures
# =============================================================================


class GenericSegment(FinTSSegment):
    """Generic segment that captures any data without strict validation.

    Used for bank-specific segments with unknown or variable structures.
    """

    # Flexible fields that can capture various data
    data1: Any = Field(default=None)
    data2: Any = Field(default=None)
    data3: Any = Field(default=None)
    data4: Any = Field(default=None)
    data5: Any = Field(default=None)
    data6: Any = Field(default=None)
    data7: Any = Field(default=None)
    data8: Any = Field(default=None)
    data9: Any = Field(default=None)
    data10: Any = Field(default=None)
    extra_data: Any = Field(default=None)


# =============================================================================
# SEPA Account Parameters (HISPAS)
# =============================================================================


class GetSEPAAccountParameter(FinTSDataElementGroup):
    """Parameter for SEPA account info request.

    Source: FinTS 3.0 Messages
    """

    single_account_query_allowed: FinTSBool | None = Field(
        default=None,
        description="Einzelkontenabruf erlaubt",
    )
    national_account_allowed: FinTSBool | None = Field(
        default=None,
        description="Nationale Kontoverbindung erlaubt",
    )
    structured_usage_allowed: FinTSBool | None = Field(
        default=None,
        description="Strukturierte Verwendungszweckangabe erlaubt",
    )
    supported_sepa_formats: list[FinTSAlphanumeric] | None = Field(
        default=None,
        description="Unterstützte SEPA-Formate",
    )


class HISPAS1(ParameterSegmentBase):
    """SEPA-Kontoverbindung anfordern, Parameter, version 1.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HISPAS"
    SEGMENT_VERSION: ClassVar[int] = 1

    parameter: GetSEPAAccountParameter | None = Field(
        default=None,
        description="Parameter SEPA-Kontoverbindung anfordern",
    )


class HISPAS2(ParameterSegmentBase):
    """SEPA-Kontoverbindung anfordern, Parameter, version 2.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HISPAS"
    SEGMENT_VERSION: ClassVar[int] = 2

    parameter: GetSEPAAccountParameter | None = Field(
        default=None,
        description="Parameter SEPA-Kontoverbindung anfordern",
    )


class HISPAS3(ParameterSegmentBase):
    """SEPA-Kontoverbindung anfordern, Parameter, version 3.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HISPAS"
    SEGMENT_VERSION: ClassVar[int] = 3

    parameter: GetSEPAAccountParameter | None = Field(
        default=None,
        description="Parameter SEPA-Kontoverbindung anfordern",
    )


# =============================================================================
# Balance Parameters (HISALS)
# =============================================================================


class BalanceParameter(FinTSDataElementGroup):
    """Parameter for balance query.

    Source: FinTS 3.0 Messages
    """

    number_of_days: FinTSNumeric | None = Field(
        default=None,
        description="Anzahl Tage",
    )
    available_balance_provided: FinTSBool | None = Field(
        default=None,
        description="Verfügbarer Betrag mitliefern",
    )


class HISALS4(ParameterSegmentBase):
    """Saldenabfrage Parameter, version 4.

    Source: HBCI Specification
    """

    SEGMENT_TYPE: ClassVar[str] = "HISALS"
    SEGMENT_VERSION: ClassVar[int] = 4

    parameter: BalanceParameter | None = Field(
        default=None,
        description="Parameter Saldenabfrage",
    )


class HISALS5(ParameterSegmentBase):
    """Saldenabfrage Parameter, version 5.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HISALS"
    SEGMENT_VERSION: ClassVar[int] = 5

    parameter: BalanceParameter | None = Field(
        default=None,
        description="Parameter Saldenabfrage",
    )


class HISALS6(ParameterSegmentBase):
    """Saldenabfrage Parameter, version 6.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HISALS"
    SEGMENT_VERSION: ClassVar[int] = 6

    parameter: BalanceParameter | None = Field(
        default=None,
        description="Parameter Saldenabfrage",
    )


class HISALS7(ParameterSegmentBase):
    """Saldenabfrage Parameter, version 7.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HISALS"
    SEGMENT_VERSION: ClassVar[int] = 7

    parameter: BalanceParameter | None = Field(
        default=None,
        description="Parameter Saldenabfrage",
    )


# =============================================================================
# Transaction Parameters (HIKAZS)
# =============================================================================


class TransactionParameter(FinTSDataElementGroup):
    """Parameter for transaction query.

    Source: FinTS 3.0 Messages
    """

    number_of_days: FinTSNumeric | None = Field(
        default=None,
        description="Anzahl Tage",
    )
    data_format: FinTSAlphanumeric | None = Field(
        default=None,
        description="Datenformat",
    )


class HIKAZS4(ParameterSegmentBase):
    """Kontoumsätze Parameter, version 4.

    Source: HBCI Specification
    """

    SEGMENT_TYPE: ClassVar[str] = "HIKAZS"
    SEGMENT_VERSION: ClassVar[int] = 4

    parameter: TransactionParameter | None = Field(
        default=None,
        description="Parameter Kontoumsätze",
    )


class HIKAZS5(ParameterSegmentBase):
    """Kontoumsätze Parameter, version 5.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIKAZS"
    SEGMENT_VERSION: ClassVar[int] = 5

    parameter: TransactionParameter | None = Field(
        default=None,
        description="Parameter Kontoumsätze",
    )


class HIKAZS6(ParameterSegmentBase):
    """Kontoumsätze Parameter, version 6.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIKAZS"
    SEGMENT_VERSION: ClassVar[int] = 6

    parameter: TransactionParameter | None = Field(
        default=None,
        description="Parameter Kontoumsätze",
    )


class HIKAZS7(ParameterSegmentBase):
    """Kontoumsätze Parameter, version 7.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIKAZS"
    SEGMENT_VERSION: ClassVar[int] = 7

    parameter: TransactionParameter | None = Field(
        default=None,
        description="Parameter Kontoumsätze",
    )


# =============================================================================
# Security Procedure Parameters (HISHV)
# Note: HISHV has a non-standard structure - NOT a parameter segment!
# =============================================================================


class HISHV3(GenericSegment):
    """Sicherheitsverfahren, version 3.

    Lists supported security procedures. Uses GenericSegment because
    the structure varies between banks and doesn't follow standard patterns.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HISHV"
    SEGMENT_VERSION: ClassVar[int] = 3


# =============================================================================
# Version Registries
# =============================================================================
#
# Note: Many bank-specific parameter segments (HIPAES, HICSAS, etc.) are NOT
# defined here. The parser automatically uses GenericSegment for unknown
# parameter segments (those matching HI???S pattern). This eliminates the need
# for hundreds of empty boilerplate class definitions.


HISPAS_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HISPAS1,
    2: HISPAS2,
    3: HISPAS3,
}

HISALS_VERSIONS: dict[int, type[FinTSSegment]] = {
    4: HISALS4,
    5: HISALS5,
    6: HISALS6,
    7: HISALS7,
}

HIKAZS_VERSIONS: dict[int, type[FinTSSegment]] = {
    4: HIKAZS4,
    5: HIKAZS5,
    6: HIKAZS6,
    7: HIKAZS7,
}

HISHV_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HISHV3,
}


__all__ = [
    # Base classes
    "ParameterSegmentBase",
    "GenericParameter",
    "GenericSegment",
    # SEPA Account
    "GetSEPAAccountParameter",
    "HISPAS1",
    "HISPAS2",
    "HISPAS3",
    "HISPAS_VERSIONS",
    # Balance
    "BalanceParameter",
    "HISALS4",
    "HISALS5",
    "HISALS6",
    "HISALS7",
    "HISALS_VERSIONS",
    # Transactions
    "TransactionParameter",
    "HIKAZS4",
    "HIKAZS5",
    "HIKAZS6",
    "HIKAZS7",
    "HIKAZS_VERSIONS",
    # Security
    "HISHV3",
    "HISHV_VERSIONS",
]
