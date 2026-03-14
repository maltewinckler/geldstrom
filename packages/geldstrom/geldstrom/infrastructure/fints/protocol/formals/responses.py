"""FinTS Response DEGs.

These DEGs handle response messages from banks.
"""
from __future__ import annotations

from pydantic import Field

from ..base import FinTSDataElementGroup
from ..types import FinTSAlphanumeric, FinTSDigits, FinTSID, FinTSNumeric


class Response(FinTSDataElementGroup):
    """Rückmeldung (Response).

    Contains a response code, reference, text, and optional parameters
    from the bank.

    Source: FinTS 3.0 Formals

    Response code ranges:
    - 0010-0100: Success
    - 3000-3999: Warning
    - 9000-9999: Error

    Example:
        response = Response.from_wire_list(["0010", "3", "Auftrag entgegengenommen"])
    """

    code: FinTSDigits = Field(
        min_length=4,
        max_length=4,
        description="Rückmeldungscode",
    )
    reference_element: FinTSAlphanumeric = Field(
        max_length=7,
        description="Bezugselement",
    )
    text: FinTSAlphanumeric = Field(
        max_length=80,
        description="Rückmeldungstext",
    )
    parameters: list[FinTSAlphanumeric] | None = Field(
        default=None,
        max_length=10,
        description="Rückmeldungsparameter",
    )

    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.code.startswith("0") or self.code.startswith("1")

    @property
    def is_warning(self) -> bool:
        """Check if response indicates a warning."""
        return self.code.startswith("3")

    @property
    def is_error(self) -> bool:
        """Check if response indicates an error."""
        return self.code.startswith("9")

    def __str__(self) -> str:
        return f"{self.code}: {self.text}"


class ReferenceMessage(FinTSDataElementGroup):
    """Bezugsnachricht (Reference Message).

    References a previous message in a dialog.

    Source: FinTS 3.0 Formals
    """

    dialog_id: FinTSID = Field(
        description="Dialog-ID",
    )
    message_number: FinTSNumeric = Field(
        ge=0,
        lt=10000,  # max 4 digits
        description="Nachrichtennummer",
    )


__all__ = [
    "Response",
    "ReferenceMessage",
]

