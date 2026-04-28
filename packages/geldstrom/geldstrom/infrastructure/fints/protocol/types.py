"""FinTS Annotated Types - wire-format validators and serializers for Pydantic models."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, PlainSerializer


def parse_fints_date(value: Any) -> date:
    if value is None:
        raise ValueError("Date cannot be None")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value = value.strip()
        if len(value) == 8 and value.isdigit():
            try:
                return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
            except ValueError as e:
                raise ValueError(f"Invalid date components in '{value}': {e}") from e
    raise ValueError(f"Cannot parse FinTS date from: {value!r}")


def parse_fints_time(value: Any) -> time:
    if value is None:
        raise ValueError("Time cannot be None")
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        value = value.strip()
        if len(value) == 6 and value.isdigit():
            try:
                return time(int(value[:2]), int(value[2:4]), int(value[4:6]))
            except ValueError as e:
                raise ValueError(f"Invalid time components in '{value}': {e}") from e
    raise ValueError(f"Cannot parse FinTS time from: {value!r}")


def parse_fints_amount(value: Any) -> Decimal:
    """Parse FinTS amount: German decimal format (comma separator) to Decimal."""
    if value is None:
        raise ValueError("Amount cannot be None")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("Amount cannot be empty string")
        try:
            # FinTS uses comma as decimal separator
            return Decimal(value.replace(",", "."))
        except InvalidOperation as e:
            raise ValueError(f"Cannot parse amount '{value}': {e}") from e
    raise ValueError(f"Cannot parse FinTS amount from: {value!r}")


def parse_fints_bool(value: Any) -> bool:
    """Parse FinTS boolean: 'J' (Ja) → True, 'N' (Nein) → False."""
    if value is None:
        raise ValueError("Boolean cannot be None")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        value = value.strip().upper()
        if value == "J":
            return True
        if value == "N":
            return False
    raise ValueError(
        f"Cannot parse FinTS boolean from: {value!r} (expected 'J' or 'N')"
    )


def parse_fints_numeric(value: Any) -> int:
    if value is None:
        raise ValueError("Numeric value cannot be None")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("Numeric value cannot be empty string")
        # Allow leading zeros - they're used in fixed-width fields like message_size
        # The semantic value is the same (000000000123 == 123)
        try:
            return int(value, 10)
        except ValueError as e:
            raise ValueError(f"Cannot parse numeric '{value}': {e}") from e
    raise ValueError(f"Cannot parse FinTS numeric from: {value!r}")


def parse_fints_digits(value: Any) -> str:
    """Parse FinTS digits: string of digits only, allows leading zeros."""
    if value is None:
        raise ValueError("Digits value cannot be None")
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        value = value.strip()
        if not value.isdigit() and value != "":
            raise ValueError(f"FinTS digits must contain only digits: {value!r}")
        return value
    raise ValueError(f"Cannot parse FinTS digits from: {value!r}")


def parse_fints_text(value: Any) -> str:
    if value is None:
        raise ValueError("Text value cannot be None")
    return str(value)


def parse_fints_binary(value: Any) -> bytes:
    if value is None:
        raise ValueError("Binary value cannot be None")
    if isinstance(value, bytes):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    raise ValueError(f"Cannot parse FinTS binary from: {type(value).__name__}")


def parse_fints_code(value: Any) -> str:
    if value is None:
        raise ValueError("Code value cannot be None")
    return str(value)


def serialize_fints_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def serialize_fints_time(value: time) -> str:
    return value.strftime("%H%M%S")


def serialize_fints_amount(value: Decimal) -> str:
    s = str(value)
    return s.replace(".", ",")


def serialize_fints_bool(value: bool) -> str:
    return "J" if value else "N"


def serialize_fints_numeric(value: int) -> str:
    return str(value)


FinTSDate = Annotated[
    date,
    BeforeValidator(parse_fints_date),
    PlainSerializer(serialize_fints_date, return_type=str),
    Field(description="FinTS date in YYYYMMDD format"),
]


FinTSTime = Annotated[
    time,
    BeforeValidator(parse_fints_time),
    PlainSerializer(serialize_fints_time, return_type=str),
    Field(description="FinTS time in HHMMSS format"),
]


FinTSAmount = Annotated[
    Decimal,
    BeforeValidator(parse_fints_amount),
    PlainSerializer(serialize_fints_amount, return_type=str),
    Field(description="FinTS amount with German decimal format (comma separator)"),
]


FinTSBool = Annotated[
    bool,
    BeforeValidator(parse_fints_bool),
    PlainSerializer(serialize_fints_bool, return_type=str),
    Field(description="FinTS boolean (J=Yes, N=No)"),
]


FinTSNumeric = Annotated[
    int,
    BeforeValidator(parse_fints_numeric),
    PlainSerializer(serialize_fints_numeric, return_type=str),
    Field(description="FinTS numeric (no leading zeros)"),
]


FinTSDigits = Annotated[
    str,
    BeforeValidator(parse_fints_digits),
    Field(description="FinTS digits (string of digits only, may have leading zeros)"),
]


FinTSText = Annotated[
    str,
    BeforeValidator(parse_fints_text),
    Field(description="FinTS text"),
]


FinTSAlphanumeric = Annotated[
    str,
    BeforeValidator(parse_fints_text),
    Field(description="FinTS alphanumeric"),
]


FinTSBinary = Annotated[
    bytes,
    BeforeValidator(parse_fints_binary),
    Field(description="FinTS binary data"),
]


FinTSCode = Annotated[
    str,
    BeforeValidator(parse_fints_code),
    Field(description="FinTS code (short identifier)"),
]


FinTSCurrency = Annotated[
    str,
    BeforeValidator(parse_fints_code),
    Field(
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code (e.g., EUR, USD)",
    ),
]


FinTSCountry = Annotated[
    str,
    BeforeValidator(parse_fints_digits),
    Field(
        min_length=3,
        max_length=3,
        pattern=r"^\d{3}$",
        description="ISO 3166 numeric country code (e.g., 280 for Germany)",
    ),
]


FinTSID = Annotated[
    str,
    BeforeValidator(parse_fints_text),
    Field(max_length=30, description="FinTS identifier (max 30 chars)"),
]


__all__ = [
    "parse_fints_amount",
    "parse_fints_binary",
    "parse_fints_bool",
    "parse_fints_code",
    "parse_fints_date",
    "parse_fints_digits",
    "parse_fints_numeric",
    "parse_fints_text",
    "parse_fints_time",
    "serialize_fints_amount",
    "serialize_fints_bool",
    "serialize_fints_date",
    "serialize_fints_numeric",
    "serialize_fints_time",
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
]
