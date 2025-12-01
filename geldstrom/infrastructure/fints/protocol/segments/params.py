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

from ..base import FinTSSegment, FinTSDataElementGroup
from ..types import (
    FinTSAlphanumeric,
    FinTSBool,
    FinTSNumeric,
)
from ..formals import SecurityProfile


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
# Statement Parameters (HIEKAS)
# =============================================================================


class StatementParameter(FinTSDataElementGroup):
    """Parameter for statement requests.

    Source: FinTS 3.0 Messages
    """

    format_supported: FinTSAlphanumeric | None = Field(
        default=None,
        description="Unterstütztes Format",
    )


class HIEKAS3(ParameterSegmentBase):
    """Kontoauszug Parameter, version 3.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIEKAS"
    SEGMENT_VERSION: ClassVar[int] = 3

    parameter: StatementParameter | None = Field(
        default=None,
        description="Parameter Kontoauszug",
    )


class HIEKAS4(ParameterSegmentBase):
    """Kontoauszug Parameter, version 4.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIEKAS"
    SEGMENT_VERSION: ClassVar[int] = 4

    parameter: StatementParameter | None = Field(
        default=None,
        description="Parameter Kontoauszug",
    )


class HIEKAS5(ParameterSegmentBase):
    """Kontoauszug Parameter, version 5.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIEKAS"
    SEGMENT_VERSION: ClassVar[int] = 5

    parameter: StatementParameter | None = Field(
        default=None,
        description="Parameter Kontoauszug",
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
# Transfer Parameters (HICCSS, HIDSCS, HIBSES, HIDSES, HIDMES, etc.)
# =============================================================================


class TransferParameter(FinTSDataElementGroup):
    """Parameter for transfer operations.

    Source: FinTS 3.0 Messages
    """

    max_amount: FinTSNumeric | None = Field(
        default=None,
        description="Maximaler Betrag",
    )
    max_usage_lines: FinTSNumeric | None = Field(
        default=None,
        description="Maximale Verwendungszweckzeilen",
    )
    supported_sepa_formats: list[FinTSAlphanumeric] | None = Field(
        default=None,
        description="Unterstützte SEPA-Formate",
    )


class HICSBase(ParameterSegmentBase):
    """Base class for HI*CS type parameter segments."""

    parameter: TransferParameter | None = Field(
        default=None,
        description="Parameter",
    )


class HICCSS1(HICSBase):
    """SEPA-Einzelüberweisung Parameter, version 1.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HICCSS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIDSCS1(HICSBase):
    """SEPA-Lastschrift Parameter, version 1.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIDSCS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIBSES1(HICSBase):
    """SEPA-Sammel-Lastschrift Parameter, version 1.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIBSES"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIDSES1(HICSBase):
    """SEPA-Einzel-Lastschrift Parameter, version 1.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIDSES"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIDMES1(HICSBase):
    """SEPA-Sammelüberweisung Parameter, version 1.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIDMES"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIBMES1(HICSBase):
    """SEPA-Sammelüberweisung (Batch) Parameter, version 1.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIBMES"
    SEGMENT_VERSION: ClassVar[int] = 1


# =============================================================================
# Other Common Parameters - Generic Implementations
# Many bank-specific segments vary in structure, so we use GenericSegment
# =============================================================================


class HIPAES1(GenericSegment):
    """Prepaid-Aufladung Parameter, version 1.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIPAES"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIPSPS1(GenericSegment):
    """PSP-Parameter, version 1.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIPSPS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIQTGS1(GenericSegment):
    """Quittungs-Parameter, version 1.

    Source: FinTS 3.0 Messages
    """

    SEGMENT_TYPE: ClassVar[str] = "HIQTGS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICSAS1(GenericSegment):
    """CSA Parameter, version 1.

    Source: Bank-specific
    """

    SEGMENT_TYPE: ClassVar[str] = "HICSAS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICSBS1(GenericSegment):
    """CSB Parameter, version 1.

    Source: Bank-specific
    """

    SEGMENT_TYPE: ClassVar[str] = "HICSBS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICSLS1(GenericSegment):
    """CSL Parameter, version 1.

    Source: Bank-specific
    """

    SEGMENT_TYPE: ClassVar[str] = "HICSLS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICSES1(GenericSegment):
    """CSE Parameter, version 1.

    Source: Bank-specific
    """

    SEGMENT_TYPE: ClassVar[str] = "HICSES"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICDBS1(GenericSegment):
    """CDB Parameter, version 1.

    Source: Bank-specific
    """

    SEGMENT_TYPE: ClassVar[str] = "HICDBS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICDLS1(GenericSegment):
    """CDL Parameter, version 1.

    Source: Bank-specific
    """

    SEGMENT_TYPE: ClassVar[str] = "HICDLS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICDNS1(GenericSegment):
    """CDN Parameter, version 1.

    Source: Bank-specific
    """

    SEGMENT_TYPE: ClassVar[str] = "HICDNS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIDSBS1(GenericSegment):
    """DSB Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIDSBS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICUBS1(GenericSegment):
    """CUB Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HICUBS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICUMS1(GenericSegment):
    """CUM Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HICUMS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICDES1(GenericSegment):
    """CDE Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HICDES"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIDSWS1(GenericSegment):
    """DSW Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIDSWS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIECAS1(GenericSegment):
    """ECA Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIECAS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIDBSS1(GenericSegment):
    """DBS Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIDBSS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIBBSS1(GenericSegment):
    """BBS Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIBBSS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIDMBS1(GenericSegment):
    """DMB Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIDMBS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIBMBS1(GenericSegment):
    """BMB Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIBMBS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICMBS1(GenericSegment):
    """CMB Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HICMBS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICMES1(GenericSegment):
    """CME Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HICMES"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICMLS1(GenericSegment):
    """CML Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HICMLS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIWPDS6(GenericSegment):
    """Depot Parameter, version 6."""

    SEGMENT_TYPE: ClassVar[str] = "HIWPDS"
    SEGMENT_VERSION: ClassVar[int] = 6


class HIWPDS7(GenericSegment):
    """Depot Parameter, version 7."""

    SEGMENT_TYPE: ClassVar[str] = "HIWPDS"
    SEGMENT_VERSION: ClassVar[int] = 7


class HIIPZS1(GenericSegment):
    """Instant Payment Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIIPZS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIIPMS1(GenericSegment):
    """Instant Payment Batch Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIIPMS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICAZS1(GenericSegment):
    """CAMT Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HICAZS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIKAUS1(GenericSegment):
    """Statement Overview Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIKAUS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIKAUS2(GenericSegment):
    """Statement Overview Parameter, version 2."""

    SEGMENT_TYPE: ClassVar[str] = "HIKAUS"
    SEGMENT_VERSION: ClassVar[int] = 2


class HIPROS5(GenericSegment):
    """Journal Parameter, version 5."""

    SEGMENT_TYPE: ClassVar[str] = "HIPROS"
    SEGMENT_VERSION: ClassVar[int] = 5


class HITABS4(GenericSegment):
    """TAN Media Parameter, version 4."""

    SEGMENT_TYPE: ClassVar[str] = "HITABS"
    SEGMENT_VERSION: ClassVar[int] = 4


class HITABS5(GenericSegment):
    """TAN Media Parameter, version 5."""

    SEGMENT_TYPE: ClassVar[str] = "HITABS"
    SEGMENT_VERSION: ClassVar[int] = 5


# Additional bank-specific segments (version 2 variants and others)


class HIBMES2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIBMES"
    SEGMENT_VERSION: ClassVar[int] = 2


class HIBSES2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIBSES"
    SEGMENT_VERSION: ClassVar[int] = 2


class HIDSES2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIDSES"
    SEGMENT_VERSION: ClassVar[int] = 2


class HIDMES2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIDMES"
    SEGMENT_VERSION: ClassVar[int] = 2


class HIWDUS5(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIWDUS"
    SEGMENT_VERSION: ClassVar[int] = 5


class HIKIFS7(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIKIFS"
    SEGMENT_VERSION: ClassVar[int] = 7


class HIBAZS1(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIBAZS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIZDFS1(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIZDFS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIDVKS2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIDVKS"
    SEGMENT_VERSION: ClassVar[int] = 2


class HIKOMS4(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIKOMS"
    SEGMENT_VERSION: ClassVar[int] = 4


class HIDSWS2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIDSWS"
    SEGMENT_VERSION: ClassVar[int] = 2


class HICCMS1(GenericSegment):
    """SEPA batch transfer param - generic to avoid conflict."""
    SEGMENT_TYPE: ClassVar[str] = "HICCMS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HICCMS2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HICCMS"
    SEGMENT_VERSION: ClassVar[int] = 2


class HIDSCS2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIDSCS"
    SEGMENT_VERSION: ClassVar[int] = 2


class HIDMCS1(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIDMCS"
    SEGMENT_VERSION: ClassVar[int] = 1


class HIDMCS2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIDMCS"
    SEGMENT_VERSION: ClassVar[int] = 2


class HIDBSS2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIDBSS"
    SEGMENT_VERSION: ClassVar[int] = 2


class HIBBSS2(GenericSegment):
    SEGMENT_TYPE: ClassVar[str] = "HIBBSS"
    SEGMENT_VERSION: ClassVar[int] = 2


# =============================================================================
# Version Registries
# =============================================================================


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

HIEKAS_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HIEKAS3,
    4: HIEKAS4,
    5: HIEKAS5,
}

HISHV_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HISHV3,
}

HICCSS_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HICCSS1,
}

HIDSCS_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HIDSCS1,
}

HIBSES_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HIBSES1,
}

HIDSES_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HIDSES1,
}

HIDMES_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HIDMES1,
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
    # Statements
    "StatementParameter",
    "HIEKAS3",
    "HIEKAS4",
    "HIEKAS5",
    "HIEKAS_VERSIONS",
    # Security
    "HISHV3",
    "HISHV_VERSIONS",
    # Transfers
    "HICSBase",
    "TransferParameter",
    "HICCSS1",
    "HIDSCS1",
    "HIBSES1",
    "HIDSES1",
    "HIDMES1",
    "HIBMES1",
    "HICCSS_VERSIONS",
    "HIDSCS_VERSIONS",
    "HIBSES_VERSIONS",
    "HIDSES_VERSIONS",
    "HIDMES_VERSIONS",
    # Bank-specific (generic)
    "HIPAES1",
    "HIPSPS1",
    "HIQTGS1",
    "HICSAS1",
    "HICSBS1",
    "HICSLS1",
    "HICSES1",
    "HICDBS1",
    "HICDLS1",
    "HICDNS1",
    "HIDSBS1",
    "HICUBS1",
    "HICUMS1",
    "HICDES1",
    "HIDSWS1",
    "HIECAS1",
    "HIDBSS1",
    "HIBBSS1",
    "HIDMBS1",
    "HIBMBS1",
    "HICMBS1",
    "HICMES1",
    "HICMLS1",
    "HIWPDS6",
    "HIWPDS7",
    "HIIPZS1",
    "HIIPMS1",
    "HICAZS1",
    "HIKAUS1",
    "HIKAUS2",
    "HIPROS5",
    "HITABS4",
    "HITABS5",
    # Version 2 variants and additional
    "HIBMES2",
    "HIBSES2",
    "HIDSES2",
    "HIDMES2",
    "HIWDUS5",
    "HIKIFS7",
    "HIBAZS1",
    "HIZDFS1",
    "HIDVKS2",
    "HIKOMS4",
    "HIDSWS2",
    "HICCMS1",
    "HICCMS2",
    "HIDSCS2",
    "HIDMCS1",
    "HIDMCS2",
    "HIDBSS2",
    "HIBBSS2",
]
