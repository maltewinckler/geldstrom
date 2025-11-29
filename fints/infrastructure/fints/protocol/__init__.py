"""FinTS Protocol Layer - Pydantic-based protocol models and parameter management.

This module provides:
1. Parameter management (BPD/UPD handling)
2. Pydantic-based protocol types and models

Key Components:
- types: Annotated types for FinTS data elements (FinTSDate, FinTSAmount, etc.)
- base: Base models (FinTSModel, FinTSSegment, SegmentSequence)
- parameters: BPD/UPD parameter stores

Example:
    from fints.infrastructure.fints.protocol import (
        FinTSModel, FinTSDate, FinTSAmount,
        ParameterStore,
    )

    class MyModel(FinTSModel):
        date: FinTSDate
        amount: FinTSAmount

    # Parses FinTS wire format automatically
    model = MyModel(date="20231225", amount="1234,56")
"""
from __future__ import annotations

# Parameter management
from .parameters import (
    BankParameters,
    ParameterStore,
    UserParameters,
)

# Base models
from .base import (
    FinTSDataElementGroup,
    FinTSModel,
    FinTSSegment,
    SegmentHeader,
    SegmentSequence,
)

# Types
from .types import (
    FinTSAlphanumeric,
    FinTSAmount,
    FinTSBinary,
    FinTSBool,
    FinTSCode,
    FinTSCountry,
    FinTSCurrency,
    FinTSDate,
    FinTSDigits,
    FinTSID,
    FinTSNumeric,
    FinTSText,
    FinTSTime,
    # Validators (for custom usage)
    parse_fints_amount,
    parse_fints_binary,
    parse_fints_bool,
    parse_fints_code,
    parse_fints_date,
    parse_fints_digits,
    parse_fints_numeric,
    parse_fints_text,
    parse_fints_time,
    # Serializers (for custom usage)
    serialize_fints_amount,
    serialize_fints_bool,
    serialize_fints_date,
    serialize_fints_numeric,
    serialize_fints_time,
)

# Segments
# Parser
from .parser import (
    FinTSParser,
    FinTSParserError,
    FinTSParserWarning,
    FinTSSerializer,
    SegmentRegistry,
    get_default_registry,
)

# Segments
from .segments import (
    # Balance segments
    HKSAL5,
    HKSAL6,
    HKSAL7,
    HKSAL_VERSIONS,
    HISAL5,
    HISAL6,
    HISAL7,
    HISAL_VERSIONS,
    # Account segments
    HKSPA1,
    HISPA1,
    # Transaction segments
    HKKAZ5,
    HKKAZ6,
    HKKAZ7,
    HKKAZ_VERSIONS,
    HIKAZ5,
    HIKAZ6,
    HIKAZ7,
    HIKAZ_VERSIONS,
    HKCAZ1,
    HKCAZ_VERSIONS,
    HICAZ1,
    HICAZ_VERSIONS,
    # Statement segments
    ReportPeriod,
    HKEKA3,
    HKEKA4,
    HKEKA5,
    HKEKA_VERSIONS,
    HIEKA3,
    HIEKA4,
    HIEKA5,
    HIEKA_VERSIONS,
    HKKAU1,
    HKKAU2,
    HKKAU_VERSIONS,
    HIKAU1,
    HIKAU2,
    HIKAU_VERSIONS,
)

__all__ = [
    # Parameter management
    "BankParameters",
    "ParameterStore",
    "UserParameters",
    # Base models
    "FinTSModel",
    "FinTSDataElementGroup",
    "FinTSSegment",
    "SegmentHeader",
    "SegmentSequence",
    # Types
    "FinTSAlphanumeric",
    "FinTSAmount",
    "FinTSBinary",
    "FinTSBool",
    "FinTSCode",
    "FinTSCountry",
    "FinTSCurrency",
    "FinTSDate",
    "FinTSDigits",
    "FinTSID",
    "FinTSNumeric",
    "FinTSText",
    "FinTSTime",
    # Validators
    "parse_fints_amount",
    "parse_fints_binary",
    "parse_fints_bool",
    "parse_fints_code",
    "parse_fints_date",
    "parse_fints_digits",
    "parse_fints_numeric",
    "parse_fints_text",
    "parse_fints_time",
    # Serializers
    "serialize_fints_amount",
    "serialize_fints_bool",
    "serialize_fints_date",
    "serialize_fints_numeric",
    "serialize_fints_time",
    # Parser
    "FinTSParser",
    "FinTSParserError",
    "FinTSParserWarning",
    "FinTSSerializer",
    "SegmentRegistry",
    "get_default_registry",
    # Balance segments
    "HKSAL5",
    "HKSAL6",
    "HKSAL7",
    "HKSAL_VERSIONS",
    "HISAL5",
    "HISAL6",
    "HISAL7",
    "HISAL_VERSIONS",
    # Account segments
    "HKSPA1",
    "HISPA1",
    # Transaction segments
    "HKKAZ5",
    "HKKAZ6",
    "HKKAZ7",
    "HKKAZ_VERSIONS",
    "HIKAZ5",
    "HIKAZ6",
    "HIKAZ7",
    "HIKAZ_VERSIONS",
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
    "HKKAU1",
    "HKKAU2",
    "HKKAU_VERSIONS",
    "HIKAU1",
    "HIKAU2",
    "HIKAU_VERSIONS",
]
