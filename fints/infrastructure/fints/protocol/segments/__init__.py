"""FinTS Protocol Segments - Pydantic models.

This module provides Pydantic-based implementations of FinTS segments,
replacing the legacy Container-based definitions in fints/segments/.

Segments are the main building blocks of FinTS messages. Each segment
has a header and type-specific data fields.

Organization:
- saldo: Balance segments (HKSAL, HISAL)
- accounts: Account segments (HKSPA, HISPA)
- transactions: Transaction segments (HKKAZ, HIKAZ, HKCAZ, HICAZ)
- statements: Statement segments (HKEKA, HIEKA, HKKAU, HIKAU)
"""
from __future__ import annotations

from .saldo import (
    # Request segments
    HKSAL5,
    HKSAL6,
    HKSAL7,
    # Response segments
    HISAL5,
    HISAL6,
    HISAL7,
    # Version registry
    HKSAL_VERSIONS,
    HISAL_VERSIONS,
)
from .accounts import (
    HKSPA1,
    HISPA1,
)
from .transactions import (
    # MT940 Request
    HKKAZ5,
    HKKAZ6,
    HKKAZ7,
    HKKAZ_VERSIONS,
    # MT940 Response
    HIKAZ5,
    HIKAZ6,
    HIKAZ7,
    HIKAZ_VERSIONS,
    # CAMT Request
    HKCAZ1,
    HKCAZ_VERSIONS,
    # CAMT Response
    HICAZ1,
    HICAZ_VERSIONS,
)
from .statements import (
    # Supporting DEGs
    ReportPeriod,
    # Statement Request
    HKEKA3,
    HKEKA4,
    HKEKA5,
    HKEKA_VERSIONS,
    # Statement Response
    HIEKA3,
    HIEKA4,
    HIEKA5,
    HIEKA_VERSIONS,
    # Statement Overview
    HKKAU1,
    HKKAU2,
    HKKAU_VERSIONS,
    HIKAU1,
    HIKAU2,
    HIKAU_VERSIONS,
)

__all__ = [
    # Balance request segments
    "HKSAL5",
    "HKSAL6",
    "HKSAL7",
    # Balance response segments
    "HISAL5",
    "HISAL6",
    "HISAL7",
    # Balance version registries
    "HKSAL_VERSIONS",
    "HISAL_VERSIONS",
    # Account segments
    "HKSPA1",
    "HISPA1",
    # MT940 Transaction segments
    "HKKAZ5",
    "HKKAZ6",
    "HKKAZ7",
    "HKKAZ_VERSIONS",
    "HIKAZ5",
    "HIKAZ6",
    "HIKAZ7",
    "HIKAZ_VERSIONS",
    # CAMT Transaction segments
    "HKCAZ1",
    "HKCAZ_VERSIONS",
    "HICAZ1",
    "HICAZ_VERSIONS",
    # Statement segments
    "ReportPeriod",
    "HKEKA3",
    "HKEKA4",
    "HKEKA5",
    "HKEKA_VERSIONS",
    "HIEKA3",
    "HIEKA4",
    "HIEKA5",
    "HIEKA_VERSIONS",
    # Statement Overview segments
    "HKKAU1",
    "HKKAU2",
    "HKKAU_VERSIONS",
    "HIKAU1",
    "HIKAU2",
    "HIKAU_VERSIONS",
]

