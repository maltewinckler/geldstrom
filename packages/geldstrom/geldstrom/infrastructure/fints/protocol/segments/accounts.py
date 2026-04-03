"""FinTS Account Segments (SEPA-Kontoverbindung)."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSSegment
from ..formals import (
    AccountIdentifier,
    AccountInternationalSEPA,
)


class HKSPA1(FinTSSegment):
    """SEPA-Kontoverbindung anfordern, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HKSPA"
    SEGMENT_VERSION: ClassVar[int] = 1

    accounts: list[AccountIdentifier] | None = Field(
        default=None,
        max_length=999,
        description="Kontoverbindung (optional filter)",
    )


class HISPA1(FinTSSegment):
    """SEPA-Kontoverbindung rückmelden, version 1."""

    SEGMENT_TYPE: ClassVar[str] = "HISPA"
    SEGMENT_VERSION: ClassVar[int] = 1

    accounts: list[AccountInternationalSEPA] | None = Field(
        default=None,
        max_length=999,
        description="SEPA-Kontoverbindung",
    )


__all__ = [
    "HKSPA1",
    "HISPA1",
]
