"""FinTS PIN/TAN Parameter Segments."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from ..base import FinTSDataElementGroup, FinTSSegment
from ..formals.enums import (
    AllowedFormat,
    DescriptionRequired,
    InitializationMode,
    PrincipalAccountRequired,
    SMSChargeAccountRequired,
    TANListNumberRequired,
    TANTimeDialogAssociation,
    TaskHashAlgorithm,
)
from ..types import (
    FinTSAlphanumeric,
    FinTSBool,
    FinTSCode,
    FinTSNumeric,
)

# =============================================================================
# Supporting DEGs
# =============================================================================


class TransactionTANRequired(FinTSDataElementGroup):
    """Geschäftsvorfall TAN-pflichtig."""

    transaction: FinTSAlphanumeric = Field(
        max_length=6,
        description="Geschäftsvorfallscode",
    )
    tan_required: FinTSBool = Field(
        description="TAN benötigt",
    )


class ParameterPinTan(FinTSDataElementGroup):
    """Parameter PIN/TAN-spezifische Informationen."""

    min_pin_length: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=100,
        description="Mindestlänge PIN",
    )
    max_pin_length: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=100,
        description="Maximallänge PIN",
    )
    max_tan_length: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=100,
        description="Maximallänge TAN",
    )
    user_id_field_text: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=30,
        description="Text Benutzerkennung-Feld",
    )
    customer_id_field_text: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=30,
        description="Text Kunden-ID-Feld",
    )
    transaction_tans_required: list[TransactionTANRequired] | None = Field(
        default=None,
        max_length=999,
        description="Geschäftsvorfälle mit TAN-Pflicht",
    )


class TwoStepParametersCommon(FinTSDataElementGroup):
    """Common fields for all two-step TAN parameters.

    All TwoStepParameters versions share these first fields.

    Note: `tan_process` is optional because some banks (e.g., DKB) omit it,
    sending the TAN process at the segment level instead.
    """

    security_function: FinTSCode = Field(
        max_length=3,
        description="Sicherheitsfunktion, kodiert",
    )
    tan_process: FinTSCode | None = Field(
        default=None,
        description="TAN-Prozess (optional, some banks omit this)",
    )
    technical_id: FinTSAlphanumeric = Field(
        max_length=32,
        description="Technische Identifikation TAN-Verfahren",
    )


class TwoStepParameters1(TwoStepParametersCommon):
    """Two-step TAN parameters, version 1.

    Earliest version with basic TAN support.
    """

    name: FinTSAlphanumeric = Field(
        max_length=30,
        description="Name des Zwei-Schritt-Verfahrens",
    )
    max_length_input: FinTSNumeric = Field(
        description="Maximale Länge des Eingabewertes",
    )
    allowed_format: AllowedFormat = Field(
        description="Erlaubtes Format im Zwei-Schritt-Verfahren",
    )
    text_return_value: FinTSAlphanumeric = Field(
        max_length=30,
        description="Text zur Belegung des Rückgabewertes",
    )
    max_length_return_value: FinTSNumeric = Field(
        description="Maximale Länge des Rückgabewertes",
    )
    number_of_supported_lists: FinTSNumeric = Field(
        description="Anzahl unterstützter aktiver TAN-Listen",
    )
    multiple_tans_allowed: FinTSBool = Field(
        description="Mehrfach-TAN erlaubt",
    )
    tan_time_delayed_allowed: FinTSBool = Field(
        description="TAN zeitversetzt/dialogübergreifend erlaubt",
    )


class TwoStepParameters2(TwoStepParametersCommon):
    """Two-step TAN parameters, version 2.

    Adds challenge class support.
    """

    name: FinTSAlphanumeric = Field(
        max_length=30,
        description="Name des Zwei-Schritt-Verfahrens",
    )
    max_length_input: FinTSNumeric = Field(
        description="Maximale Länge des Eingabewertes",
    )
    allowed_format: AllowedFormat = Field(
        description="Erlaubtes Format im Zwei-Schritt-Verfahren",
    )
    text_return_value: FinTSAlphanumeric = Field(
        max_length=30,
        description="Text zur Belegung des Rückgabewertes",
    )
    max_length_return_value: FinTSNumeric = Field(
        description="Maximale Länge des Rückgabewertes",
    )
    number_of_supported_lists: FinTSNumeric = Field(
        description="Anzahl unterstützter aktiver TAN-Listen",
    )
    multiple_tans_allowed: FinTSBool = Field(
        description="Mehrfach-TAN erlaubt",
    )
    tan_time_dialog_association: TANTimeDialogAssociation = Field(
        description="TAN Zeit- und Dialogbezug",
    )
    tan_list_number_required: TANListNumberRequired = Field(
        description="TAN-Listennummer erforderlich",
    )
    cancel_allowed: FinTSBool = Field(
        description="Auftragsstorno erlaubt",
    )
    challenge_class_required: FinTSBool = Field(
        description="Challenge-Klasse erforderlich",
    )
    challenge_value_required: FinTSBool = Field(
        description="Challenge-Betrag erforderlich",
    )


class TwoStepParameters3(TwoStepParametersCommon):
    """Two-step TAN parameters, version 3.

    Adds initialization mode and TAN media description.
    """

    name: FinTSAlphanumeric = Field(
        max_length=30,
        description="Name des Zwei-Schritt-Verfahrens",
    )
    max_length_input: FinTSNumeric = Field(
        description="Maximale Länge des Eingabewertes",
    )
    allowed_format: AllowedFormat = Field(
        description="Erlaubtes Format im Zwei-Schritt-Verfahren",
    )
    text_return_value: FinTSAlphanumeric = Field(
        max_length=30,
        description="Text zur Belegung des Rückgabewertes",
    )
    max_length_return_value: FinTSNumeric = Field(
        description="Maximale Länge des Rückgabewertes",
    )
    number_of_supported_lists: FinTSNumeric = Field(
        description="Anzahl unterstützter aktiver TAN-Listen",
    )
    multiple_tans_allowed: FinTSBool = Field(
        description="Mehrfach-TAN erlaubt",
    )
    tan_time_dialog_association: TANTimeDialogAssociation = Field(
        description="TAN Zeit- und Dialogbezug",
    )
    tan_list_number_required: TANListNumberRequired = Field(
        description="TAN-Listennummer erforderlich",
    )
    cancel_allowed: FinTSBool = Field(
        description="Auftragsstorno erlaubt",
    )
    challenge_class_required: FinTSBool = Field(
        description="Challenge-Klasse erforderlich",
    )
    challenge_value_required: FinTSBool = Field(
        description="Challenge-Betrag erforderlich",
    )
    initialization_mode: InitializationMode = Field(
        description="Initialisierungsmodus",
    )
    description_required: DescriptionRequired = Field(
        description="Bezeichnung des TAN-Medium erforderlich",
    )
    supported_media_number: FinTSNumeric | None = Field(
        default=None,
        description="Anzahl unterstützter aktiver TAN-Medien",
    )


class TwoStepParameters4(TwoStepParametersCommon):
    """Two-step TAN parameters, version 4.

    Adds ZKA identification and SMS charge account.
    """

    zka_id: FinTSAlphanumeric = Field(
        max_length=32,
        description="ZKA TAN-Verfahren",
    )
    zka_version: FinTSAlphanumeric = Field(
        max_length=10,
        description="Version ZKA TAN-Verfahren",
    )
    name: FinTSAlphanumeric = Field(
        max_length=30,
        description="Name des Zwei-Schritt-Verfahrens",
    )
    max_length_input: FinTSNumeric = Field(
        description="Maximale Länge des Eingabewertes",
    )
    allowed_format: AllowedFormat = Field(
        description="Erlaubtes Format im Zwei-Schritt-Verfahren",
    )
    text_return_value: FinTSAlphanumeric = Field(
        max_length=30,
        description="Text zur Belegung des Rückgabewertes",
    )
    max_length_return_value: FinTSNumeric = Field(
        description="Maximale Länge des Rückgabewertes",
    )
    number_of_supported_lists: FinTSNumeric = Field(
        description="Anzahl unterstützter aktiver TAN-Listen",
    )
    multiple_tans_allowed: FinTSBool = Field(
        description="Mehrfach-TAN erlaubt",
    )
    tan_time_dialog_association: TANTimeDialogAssociation = Field(
        description="TAN Zeit- und Dialogbezug",
    )
    tan_list_number_required: TANListNumberRequired = Field(
        description="TAN-Listennummer erforderlich",
    )
    cancel_allowed: FinTSBool = Field(
        description="Auftragsstorno erlaubt",
    )
    sms_charge_account_required: FinTSBool = Field(
        description="SMS-Abbuchungskonto erforderlich",
    )
    challenge_class_required: FinTSBool = Field(
        description="Challenge-Klasse erforderlich",
    )
    challenge_value_required: FinTSBool = Field(
        description="Challenge-Betrag erforderlich",
    )
    challenge_structured: FinTSBool = Field(
        description="Challenge strukturiert",
    )
    initialization_mode: InitializationMode = Field(
        description="Initialisierungsmodus",
    )
    description_required: DescriptionRequired = Field(
        description="Bezeichnung des TAN-Medium erforderlich",
    )
    supported_media_number: FinTSNumeric | None = Field(
        default=None,
        description="Anzahl unterstützter aktiver TAN-Medien",
    )


class TwoStepParameters5(TwoStepParametersCommon):
    """Two-step TAN parameters, version 5.

    Adds principal account required codes.
    """

    zka_id: FinTSAlphanumeric = Field(
        max_length=32,
        description="ZKA TAN-Verfahren",
    )
    zka_version: FinTSAlphanumeric = Field(
        max_length=10,
        description="Version ZKA TAN-Verfahren",
    )
    name: FinTSAlphanumeric = Field(
        max_length=30,
        description="Name des Zwei-Schritt-Verfahrens",
    )
    max_length_input: FinTSNumeric = Field(
        description="Maximale Länge des Eingabewertes",
    )
    allowed_format: AllowedFormat = Field(
        description="Erlaubtes Format im Zwei-Schritt-Verfahren",
    )
    text_return_value: FinTSAlphanumeric = Field(
        max_length=30,
        description="Text zur Belegung des Rückgabewertes",
    )
    max_length_return_value: FinTSNumeric = Field(
        description="Maximale Länge des Rückgabewertes",
    )
    number_of_supported_lists: FinTSNumeric = Field(
        description="Anzahl unterstützter aktiver TAN-Listen",
    )
    multiple_tans_allowed: FinTSBool = Field(
        description="Mehrfach-TAN erlaubt",
    )
    tan_time_dialog_association: TANTimeDialogAssociation = Field(
        description="TAN Zeit- und Dialogbezug",
    )
    tan_list_number_required: TANListNumberRequired = Field(
        description="TAN-Listennummer erforderlich",
    )
    cancel_allowed: FinTSBool = Field(
        description="Auftragsstorno erlaubt",
    )
    sms_charge_account_required: SMSChargeAccountRequired = Field(
        description="SMS-Abbuchungskonto erforderlich",
    )
    principal_account_required: PrincipalAccountRequired = Field(
        description="Auftraggeberkonto erforderlich",
    )
    challenge_class_required: FinTSBool = Field(
        description="Challenge-Klasse erforderlich",
    )
    challenge_structured: FinTSBool = Field(
        description="Challenge strukturiert",
    )
    initialization_mode: InitializationMode = Field(
        description="Initialisierungsmodus",
    )
    description_required: DescriptionRequired = Field(
        description="Bezeichnung des TAN-Medium erforderlich",
    )
    supported_media_number: FinTSNumeric | None = Field(
        default=None,
        description="Anzahl unterstützter aktiver TAN-Medien",
    )


class TwoStepParameters6(TwoStepParametersCommon):
    """Two-step TAN parameters, version 6.

    Adds response HHD_UC required.

    Note: Most fields are optional because banks may send incomplete data.
    The legacy parser handles this gracefully, and we preserve that behavior.

    Some banks (e.g., DKB) omit the `tan_process` field entirely. The
    `from_wire_list` method detects this by checking if the value at position 1
    looks like a technical_id (more than 1 character) rather than a TAN process
    code ('1'-'4').
    """

    zka_id: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=32,
        description="ZKA TAN-Verfahren",
    )
    zka_version: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=10,
        description="Version ZKA TAN-Verfahren",
    )
    name: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=30,
        description="Name des Zwei-Schritt-Verfahrens",
    )
    max_length_input: FinTSNumeric | None = Field(
        default=None,
        description="Maximale Länge des Eingabewertes",
    )
    allowed_format: AllowedFormat | None = Field(
        default=None,
        description="Erlaubtes Format im Zwei-Schritt-Verfahren",
    )
    text_return_value: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=30,
        description="Text zur Belegung des Rückgabewertes",
    )
    max_length_return_value: FinTSNumeric | None = Field(
        default=None,
        description="Maximale Länge des Rückgabewertes",
    )
    multiple_tans_allowed: FinTSBool | None = Field(
        default=None,
        description="Mehrfach-TAN erlaubt",
    )
    tan_time_dialog_association: TANTimeDialogAssociation | None = Field(
        default=None,
        description="TAN Zeit- und Dialogbezug",
    )
    cancel_allowed: FinTSBool | None = Field(
        default=None,
        description="Auftragsstorno erlaubt",
    )
    sms_charge_account_required: SMSChargeAccountRequired | None = Field(
        default=None,
        description="SMS-Abbuchungskonto erforderlich",
    )
    principal_account_required: PrincipalAccountRequired | None = Field(
        default=None,
        description="Auftraggeberkonto erforderlich",
    )
    challenge_class_required: FinTSBool | None = Field(
        default=None,
        description="Challenge-Klasse erforderlich",
    )
    challenge_structured: FinTSBool | None = Field(
        default=None,
        description="Challenge strukturiert",
    )
    initialization_mode: InitializationMode | None = Field(
        default=None,
        description="Initialisierungsmodus",
    )
    description_required: DescriptionRequired | None = Field(
        default=None,
        description="Bezeichnung des TAN-Medium erforderlich",
    )
    response_hhd_uc_required: FinTSBool | None = Field(
        default=None,
        description="Antwort HHD_UC erforderlich",
    )
    supported_media_number: FinTSNumeric | None = Field(
        default=None,
        description="Anzahl unterstützter aktiver TAN-Medien",
    )

    @classmethod
    def from_wire_list(cls, data: list[Any] | None) -> TwoStepParameters6:
        """Parse from wire data, handling banks that omit tan_process.

        Some banks (e.g., DKB) omit the tan_process field entirely, causing all
        subsequent fields to shift left. We detect this by checking if the value
        at position 1 looks like a technical_id (>1 character) rather than a
        TAN process code ('1'-'4').
        """
        if data and len(data) >= 2:
            # tan_process should be at position 1
            # If it's longer than 1 char and not a digit, it's probably technical_id
            possible_tan_process = data[1]
            if (
                possible_tan_process is not None
                and isinstance(possible_tan_process, str)
                and (
                    len(possible_tan_process) > 1 or not possible_tan_process.isdigit()
                )
            ):
                # tan_process was omitted, insert None at position 1
                data = [data[0], None] + data[1:]

        return super().from_wire_list(data)


class TwoStepParameters7(TwoStepParameters6):
    """Two-step TAN parameters, version 7.

    Latest version with full decoupled TAN support.
    """

    decoupled_max_poll_number: FinTSNumeric | None = Field(
        default=None,
        description="Maximale Anzahl Statusabfragen (Decoupled)",
    )
    wait_before_first_poll: FinTSNumeric | None = Field(
        default=None,
        description="Wartezeit vor erster Statusabfrage (Sekunden)",
    )
    wait_before_next_poll: FinTSNumeric | None = Field(
        default=None,
        description="Wartezeit vor nächster Statusabfrage (Sekunden)",
    )
    manual_confirmation_allowed: FinTSBool | None = Field(
        default=None,
        description="Manuelle Bestätigung bei Decoupled erlaubt",
    )
    automated_polling_allowed: FinTSBool | None = Field(
        default=None,
        description="Automatische Statusabfragen bei Decoupled erlaubt",
    )


# Keep TwoStepParametersBase as alias for backwards compatibility
TwoStepParametersBase = TwoStepParametersCommon


class ParameterTwostepCommon(FinTSDataElementGroup):
    """Common two-step TAN parameters.

    Contains fields common to all HITANS versions.
    """

    one_step_allowed: FinTSBool = Field(
        description="Ein-Schritt-Verfahren erlaubt",
    )
    multiple_tasks_allowed: FinTSBool = Field(
        description="Mehrere Aufträge in einer Nachricht erlaubt",
    )
    task_hash_algorithm: TaskHashAlgorithm = Field(
        description="Auftrags-Hashwertverfahren",
    )


class ParameterTwostepTAN1(ParameterTwostepCommon):
    """Parameter for HITANS1.

    Version 1 includes security_profile_bank_signature.
    """

    security_profile_bank_signature: FinTSCode = Field(
        description="Sicherheitsprofil Banksignatur",
    )
    twostep_parameters: list[TwoStepParameters1] = Field(
        min_length=1,
        max_length=98,
        description="Zwei-Schritt-TAN-Parameter",
    )


class ParameterTwostepTAN2(ParameterTwostepCommon):
    """Parameter for HITANS2."""

    twostep_parameters: list[TwoStepParameters2] = Field(
        min_length=1,
        max_length=98,
        description="Zwei-Schritt-TAN-Parameter",
    )


class ParameterTwostepTAN3(ParameterTwostepCommon):
    """Parameter for HITANS3."""

    twostep_parameters: list[TwoStepParameters3] = Field(
        min_length=1,
        max_length=98,
        description="Zwei-Schritt-TAN-Parameter",
    )


class ParameterTwostepTAN4(ParameterTwostepCommon):
    """Parameter for HITANS4."""

    twostep_parameters: list[TwoStepParameters4] = Field(
        min_length=1,
        max_length=98,
        description="Zwei-Schritt-TAN-Parameter",
    )


class ParameterTwostepTAN5(ParameterTwostepCommon):
    """Parameter for HITANS5."""

    twostep_parameters: list[TwoStepParameters5] = Field(
        min_length=1,
        max_length=98,
        description="Zwei-Schritt-TAN-Parameter",
    )


class ParameterTwostepTAN6(ParameterTwostepCommon):
    """Parameter for HITANS6."""

    twostep_parameters: list[TwoStepParameters6] = Field(
        min_length=1,
        max_length=98,
        description="Zwei-Schritt-TAN-Parameter",
    )


class ParameterTwostepTAN7(ParameterTwostepCommon):
    """Parameter for HITANS7."""

    twostep_parameters: list[TwoStepParameters7] = Field(
        min_length=1,
        max_length=98,
        description="Zwei-Schritt-TAN-Parameter",
    )


# =============================================================================
# PIN/TAN Parameter Segments
# =============================================================================


class ParameterSegmentBase(FinTSSegment):
    """Base class for parameter segments.

    All parameter segments have max_number_tasks, min_number_signatures,
    and security_class fields.
    """

    max_number_tasks: FinTSNumeric = Field(
        ge=0,
        lt=1000,
        description="Maximale Anzahl Aufträge",
    )
    min_number_signatures: FinTSNumeric = Field(
        ge=0,
        lt=10,
        description="Anzahl Signaturen mindestens",
    )
    security_class: FinTSNumeric = Field(
        ge=0,
        lt=10,
        description="Sicherheitsklasse",
    )


class HIPINS1(ParameterSegmentBase):
    """PIN/TAN-spezifische Informationen, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HIPINS"
    SEGMENT_VERSION: ClassVar[int] = 1

    parameter: ParameterPinTan = Field(
        description="Parameter PIN/TAN-spezifische Informationen",
    )


class HITANS1(ParameterSegmentBase):
    """Zwei-Schritt-TAN Parameter, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HITANS"
    SEGMENT_VERSION: ClassVar[int] = 1

    parameter: ParameterTwostepTAN1 = Field(
        description="Parameter Zwei-Schritt-TAN",
    )


class HITANS2(ParameterSegmentBase):
    """Zwei-Schritt-TAN Parameter, version 2."""

    SEGMENT_TYPE: ClassVar[str] = "HITANS"
    SEGMENT_VERSION: ClassVar[int] = 2

    parameter: ParameterTwostepTAN2 = Field(
        description="Parameter Zwei-Schritt-TAN",
    )


class HITANS3(ParameterSegmentBase):
    """Zwei-Schritt-TAN Parameter, version 3."""

    SEGMENT_TYPE: ClassVar[str] = "HITANS"
    SEGMENT_VERSION: ClassVar[int] = 3

    parameter: ParameterTwostepTAN3 = Field(
        description="Parameter Zwei-Schritt-TAN",
    )


class HITANS4(ParameterSegmentBase):
    """Zwei-Schritt-TAN Parameter, version 4."""

    SEGMENT_TYPE: ClassVar[str] = "HITANS"
    SEGMENT_VERSION: ClassVar[int] = 4

    parameter: ParameterTwostepTAN4 = Field(
        description="Parameter Zwei-Schritt-TAN",
    )


class HITANS5(ParameterSegmentBase):
    """Zwei-Schritt-TAN Parameter, version 5."""

    SEGMENT_TYPE: ClassVar[str] = "HITANS"
    SEGMENT_VERSION: ClassVar[int] = 5

    parameter: ParameterTwostepTAN5 = Field(
        description="Parameter Zwei-Schritt-TAN",
    )


class HITANS6(ParameterSegmentBase):
    """Zwei-Schritt-TAN Parameter, version 6."""

    SEGMENT_TYPE: ClassVar[str] = "HITANS"
    SEGMENT_VERSION: ClassVar[int] = 6

    parameter: ParameterTwostepTAN6 = Field(
        description="Parameter Zwei-Schritt-TAN",
    )


class HITANS7(ParameterSegmentBase):
    """Zwei-Schritt-TAN Parameter, version 7.

    Contains two-step TAN procedure parameters with decoupled TAN support.
    """

    SEGMENT_TYPE: ClassVar[str] = "HITANS"
    SEGMENT_VERSION: ClassVar[int] = 7

    parameter: ParameterTwostepTAN7 = Field(
        description="Parameter Zwei-Schritt-TAN",
    )


# =============================================================================
# Version Registries
# =============================================================================


HIPINS_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HIPINS1,
}

HITANS_VERSIONS: dict[int, type[ParameterSegmentBase]] = {
    1: HITANS1,
    2: HITANS2,
    3: HITANS3,
    4: HITANS4,
    5: HITANS5,
    6: HITANS6,
    7: HITANS7,
}


__all__ = [
    # Supporting DEGs
    "TransactionTANRequired",
    "ParameterPinTan",
    "TwoStepParametersCommon",
    "TwoStepParametersBase",  # Alias for backwards compatibility
    "TwoStepParameters1",
    "TwoStepParameters2",
    "TwoStepParameters3",
    "TwoStepParameters4",
    "TwoStepParameters5",
    "TwoStepParameters6",
    "TwoStepParameters7",
    "ParameterTwostepCommon",
    "ParameterTwostepTAN1",
    "ParameterTwostepTAN2",
    "ParameterTwostepTAN3",
    "ParameterTwostepTAN4",
    "ParameterTwostepTAN5",
    "ParameterTwostepTAN6",
    "ParameterTwostepTAN7",
    # Base
    "ParameterSegmentBase",
    # Segments
    "HIPINS1",
    "HITANS1",
    "HITANS2",
    "HITANS3",
    "HITANS4",
    "HITANS5",
    "HITANS6",
    "HITANS7",
    # Registries
    "HIPINS_VERSIONS",
    "HITANS_VERSIONS",
]
