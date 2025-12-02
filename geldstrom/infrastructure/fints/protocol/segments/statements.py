"""FinTS Statement Segments (Kontoauszüge).

Request segments (HKEKA) request account statements.
Response segments (HIEKA) contain statement documents.
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSDataElementGroup, FinTSSegment
from ..formals import (
    AccountIdentifier,
    AccountInternational,
    Confirmation,
    StatementFormat,
)
from ..types import (
    FinTSAlphanumeric,
    FinTSBinary,
    FinTSBool,
    FinTSDate,
    FinTSNumeric,
    FinTSText,
    FinTSTime,
)

# =============================================================================
# Supporting DEGs
# =============================================================================


class ReportPeriod(FinTSDataElementGroup):
    """Berichtszeitraum (Report Period).

    Defines the date range covered by a statement.
    """

    start_date: FinTSDate = Field(
        description="Startdatum",
    )
    end_date: FinTSDate | None = Field(
        default=None,
        description="Enddatum",
    )


# =============================================================================
# Statement Request Segments (HKEKA)
# =============================================================================

# Note: Field order is critical in FinTS! The `account` field MUST come before
# other fields. We cannot use inheritance for common fields because Pydantic
# puts parent class fields first.


class HKEKA3(FinTSSegment):
    """Kontoauszug anfordern, version 3.

    Request account statement using Account3 format.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKEKA"
    SEGMENT_VERSION: ClassVar[int] = 3

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )
    statement_format: StatementFormat | None = Field(
        default=None,
        description="Kontoauszugsformat",
    )
    statement_number: FinTSNumeric = Field(
        ge=0,
        lt=100000,
        description="Kontoauszugsnummer",
    )
    statement_year: FinTSNumeric = Field(
        ge=1900,
        lt=10000,
        description="Kontoauszugsjahr",
    )
    max_number_responses: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Maximale Anzahl Einträge",
    )
    touchdown_point: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Aufsetzpunkt für Fortsetzung",
    )


class HKEKA4(FinTSSegment):
    """Kontoauszug anfordern, version 4.

    Request account statement using international account format.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKEKA"
    SEGMENT_VERSION: ClassVar[int] = 4

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
    statement_format: StatementFormat | None = Field(
        default=None,
        description="Kontoauszugsformat",
    )
    statement_number: FinTSNumeric = Field(
        ge=0,
        lt=100000,
        description="Kontoauszugsnummer",
    )
    statement_year: FinTSNumeric = Field(
        ge=1900,
        lt=10000,
        description="Kontoauszugsjahr",
    )
    max_number_responses: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Maximale Anzahl Einträge",
    )
    touchdown_point: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Aufsetzpunkt für Fortsetzung",
    )


class HKEKA5(FinTSSegment):
    """Kontoauszug anfordern, version 5.

    Request account statement using international account format.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKEKA"
    SEGMENT_VERSION: ClassVar[int] = 5

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
    statement_format: StatementFormat | None = Field(
        default=None,
        description="Kontoauszugsformat",
    )
    statement_number: FinTSNumeric = Field(
        ge=0,
        lt=100000,
        description="Kontoauszugsnummer",
    )
    statement_year: FinTSNumeric = Field(
        ge=1900,
        lt=10000,
        description="Kontoauszugsjahr",
    )
    max_number_responses: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Maximale Anzahl Einträge",
    )
    touchdown_point: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Aufsetzpunkt für Fortsetzung",
    )


# Type alias for backwards compatibility
HKEKABase = HKEKA3

HKEKA_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HKEKA3,
    4: HKEKA4,
    5: HKEKA5,
}


# =============================================================================
# Statement Response Segments (HIEKA)
# =============================================================================


class HIEKABase(FinTSSegment):
    """Base class for statement response segments."""

    SEGMENT_TYPE: ClassVar[str] = "HIEKA"

    statement_format: StatementFormat | None = Field(
        default=None,
        description="Kontoauszugsformat",
    )
    statement_period: ReportPeriod = Field(
        description="Berichtszeitraum",
    )
    data: FinTSBinary = Field(
        description="Kontoauszugsdaten (PDF/MT940)",
    )
    statement_info: FinTSText | None = Field(
        default=None,
        max_length=65536,
        description="Informationen zum Rechnungsabschluss",
    )
    customer_info: FinTSText | None = Field(
        default=None,
        max_length=65536,
        description="Informationen zu Kundenbedingungen",
    )
    advertising_text: FinTSText | None = Field(
        default=None,
        max_length=65536,
        description="Werbetext",
    )
    account_iban: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=34,
        description="IBAN Konto",
    )
    account_bic: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=11,
        description="BIC Konto",
    )
    statement_name_1: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Auszugsname 1",
    )
    statement_name_2: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Auszugsname 2",
    )
    statement_name_extra: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Namenszusatz",
    )
    confirmation_code: FinTSBinary | None = Field(
        default=None,
        description="Quittungscode",
    )


class HIEKA3(HIEKABase):
    """Kontoauszug, version 3.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 3


class HIEKA4(HIEKABase):
    """Kontoauszug, version 4.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 4


class HIEKA5(HIEKABase):
    """Kontoauszug, version 5.

    Includes additional date/number fields.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 5

    date_created: FinTSDate | None = Field(
        default=None,
        description="Erstellungsdatum Kontoauszug",
    )
    statement_year: FinTSNumeric | None = Field(
        default=None,
        ge=1900,
        lt=10000,
        description="Kontoauszugsjahr",
    )
    statement_number: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=100000,
        description="Kontoauszugsnummer",
    )


HIEKA_VERSIONS: dict[int, type[HIEKABase]] = {
    3: HIEKA3,
    4: HIEKA4,
    5: HIEKA5,
}


# =============================================================================
# Statement Overview Segments (HKKAU/HIKAU)
# =============================================================================


class HKKAU1(FinTSSegment):
    """Übersicht Kontoauszüge, version 1.

    Request list of available account statements.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKKAU"
    SEGMENT_VERSION: ClassVar[int] = 1

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )
    max_number_responses: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Maximale Anzahl Einträge",
    )
    touchdown_point: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Aufsetzpunkt",
    )


class HKKAU2(FinTSSegment):
    """Übersicht Kontoauszüge, version 2.

    Request list of available account statements (international).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKKAU"
    SEGMENT_VERSION: ClassVar[int] = 2

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
    max_number_responses: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Maximale Anzahl Einträge",
    )
    touchdown_point: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Aufsetzpunkt",
    )


class HIKAUBase(FinTSSegment):
    """Base for statement overview response."""

    SEGMENT_TYPE: ClassVar[str] = "HIKAU"

    statement_number: FinTSNumeric = Field(
        ge=0,
        lt=100000,
        description="Kontoauszugsnummer",
    )
    confirmation: Confirmation = Field(
        description="Quittierung",
    )
    collection_possible: FinTSBool = Field(
        description="Abholung möglich J/N",
    )
    year: FinTSNumeric | None = Field(
        default=None,
        ge=1900,
        lt=10000,
        description="Jahr",
    )
    date_created: FinTSDate | None = Field(
        default=None,
        description="Datum der Erstellung",
    )
    time_created: FinTSTime | None = Field(
        default=None,
        description="Uhrzeit der Erstellung",
    )
    creation_type: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=30,
        description="Erstellart",
    )


class HIKAU1(HIKAUBase):
    """Übersicht Kontoauszüge, version 1.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 1


class HIKAU2(HIKAUBase):
    """Übersicht Kontoauszüge, version 2.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 2


HKKAU_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HKKAU1,
    2: HKKAU2,
}

HIKAU_VERSIONS: dict[int, type[HIKAUBase]] = {
    1: HIKAU1,
    2: HIKAU2,
}


__all__ = [
    # Supporting DEGs
    "ReportPeriod",
    # Statement Request
    "HKEKABase",
    "HKEKA3",
    "HKEKA4",
    "HKEKA5",
    "HKEKA_VERSIONS",
    # Statement Response
    "HIEKABase",
    "HIEKA3",
    "HIEKA4",
    "HIEKA5",
    "HIEKA_VERSIONS",
    # Statement Overview Request
    "HKKAU1",
    "HKKAU2",
    "HKKAU_VERSIONS",
    # Statement Overview Response
    "HIKAUBase",
    "HIKAU1",
    "HIKAU2",
    "HIKAU_VERSIONS",
]

