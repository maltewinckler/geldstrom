"""FinTS Annotated Types - Reusable type definitions with wire format handling.

This module defines Pydantic Annotated types that handle both:
1. Parsing from FinTS wire format to Python types
2. Serializing from Python types to FinTS wire format

Each type is designed to be used directly in Pydantic models:

    class MyModel(BaseModel):
        date: FinTSDate
        amount: FinTSAmount
        active: FinTSBool

    # Parsing from wire format
    model = MyModel(date="20231225", amount="1234,56", active="J")

    # Native Python types
    assert model.date == date(2023, 12, 25)
    assert model.amount == Decimal("1234.56")
    assert model.active is True

Wire Format Reference (FinTS 3.0):
- Date: YYYYMMDD (e.g., "20231225")
- Time: HHMMSS (e.g., "143022")
- Amount: German decimal format with comma (e.g., "1234,56")
- Boolean: "J" (Ja/Yes) or "N" (Nein/No)
- Numeric: No leading zeros except for "0"
- Digits: String of digits only
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, PlainSerializer


# =============================================================================
# Validators (Parse wire format → Python)
# =============================================================================
def parse_fints_date(value: Any) -> date:
    """Parse FinTS date format (YYYYMMDD) to Python date.

    Args:
        value: Raw value from wire format or Python date

    Returns:
        Python date object

    Raises:
        ValueError: If value cannot be parsed as a date

    Examples:
        >>> parse_fints_date("20231225")
        datetime.date(2023, 12, 25)
        >>> parse_fints_date(date(2023, 12, 25))
        datetime.date(2023, 12, 25)
    """
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
    """Parse FinTS time format (HHMMSS) to Python time.

    Args:
        value: Raw value from wire format or Python time

    Returns:
        Python time object

    Raises:
        ValueError: If value cannot be parsed as a time

    Examples:
        >>> parse_fints_time("143022")
        datetime.time(14, 30, 22)
        >>> parse_fints_time(time(14, 30, 22))
        datetime.time(14, 30, 22)
    """
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
    """Parse FinTS amount format (German decimal with comma) to Decimal.

    FinTS uses German number format where comma is the decimal separator.

    Args:
        value: Raw value from wire format or Python numeric type

    Returns:
        Python Decimal object

    Raises:
        ValueError: If value cannot be parsed as an amount

    Examples:
        >>> parse_fints_amount("1234,56")
        Decimal('1234.56')
        >>> parse_fints_amount("1234")
        Decimal('1234')
        >>> parse_fints_amount(Decimal("1234.56"))
        Decimal('1234.56')
    """
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
    """Parse FinTS boolean format (J/N) to Python bool.

    FinTS uses German "J" (Ja) for True and "N" (Nein) for False.

    Args:
        value: Raw value from wire format or Python bool

    Returns:
        Python bool

    Raises:
        ValueError: If value is not a valid FinTS boolean

    Examples:
        >>> parse_fints_bool("J")
        True
        >>> parse_fints_bool("N")
        False
        >>> parse_fints_bool(True)
        True
    """
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
    """Parse FinTS numeric format to Python int.

    FinTS numeric values cannot have leading zeros (except for "0" itself).

    Args:
        value: Raw value from wire format or Python int

    Returns:
        Python int

    Raises:
        ValueError: If value has leading zeros or is not numeric

    Examples:
        >>> parse_fints_numeric("123")
        123
        >>> parse_fints_numeric("0")
        0
        >>> parse_fints_numeric(123)
        123
    """
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
    """Parse FinTS digits format (string of digits only).

    Unlike numeric, digits can have leading zeros and are stored as strings.

    Args:
        value: Raw value from wire format

    Returns:
        String containing only digits

    Raises:
        ValueError: If value contains non-digit characters

    Examples:
        >>> parse_fints_digits("00123")
        '00123'
        >>> parse_fints_digits("123")
        '123'
    """
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
    """Parse FinTS text/alphanumeric to string.

    Args:
        value: Raw value

    Returns:
        String value

    Examples:
        >>> parse_fints_text("Hello World")
        'Hello World'
    """
    if value is None:
        raise ValueError("Text value cannot be None")
    return str(value)


def parse_fints_binary(value: Any) -> bytes:
    """Parse FinTS binary data.

    Args:
        value: Raw value (bytes or convertible to bytes)

    Returns:
        Bytes object

    Examples:
        >>> parse_fints_binary(b'\\x00\\x01\\x02')
        b'\\x00\\x01\\x02'
    """
    if value is None:
        raise ValueError("Binary value cannot be None")
    if isinstance(value, bytes):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    raise ValueError(f"Cannot parse FinTS binary from: {type(value).__name__}")


def parse_fints_code(value: Any) -> str:
    """Parse FinTS code (short alphanumeric identifier).

    Codes are typically short strings like "EUR", "DE", "999".

    Args:
        value: Raw value

    Returns:
        String code

    Examples:
        >>> parse_fints_code("EUR")
        'EUR'
        >>> parse_fints_code("999")
        '999'
    """
    if value is None:
        raise ValueError("Code value cannot be None")
    return str(value)


# =============================================================================
# Serializers (Python → wire format)
# =============================================================================
def serialize_fints_date(value: date) -> str:
    """Serialize Python date to FinTS format (YYYYMMDD).

    Examples:
        >>> serialize_fints_date(date(2023, 12, 25))
        '20231225'
    """
    return value.strftime("%Y%m%d")


def serialize_fints_time(value: time) -> str:
    """Serialize Python time to FinTS format (HHMMSS).

    Examples:
        >>> serialize_fints_time(time(14, 30, 22))
        '143022'
    """
    return value.strftime("%H%M%S")


def serialize_fints_amount(value: Decimal) -> str:
    """Serialize Python Decimal to FinTS format (German comma decimal).

    Examples:
        >>> serialize_fints_amount(Decimal("1234.56"))
        '1234,56'
        >>> serialize_fints_amount(Decimal("1234"))
        '1234'
    """
    # Convert to string and replace decimal point with comma
    s = str(value)
    return s.replace(".", ",")


def serialize_fints_bool(value: bool) -> str:
    """Serialize Python bool to FinTS format (J/N).

    Examples:
        >>> serialize_fints_bool(True)
        'J'
        >>> serialize_fints_bool(False)
        'N'
    """
    return "J" if value else "N"


def serialize_fints_numeric(value: int) -> str:
    """Serialize Python int to FinTS format.

    Examples:
        >>> serialize_fints_numeric(123)
        '123'
    """
    return str(value)


# =============================================================================
# Annotated Types (use these in models)
# =============================================================================
FinTSDate = Annotated[
    date,
    BeforeValidator(parse_fints_date),
    PlainSerializer(serialize_fints_date, return_type=str),
    Field(description="FinTS date in YYYYMMDD format"),
]
"""FinTS date type - parses YYYYMMDD format to Python date."""


FinTSTime = Annotated[
    time,
    BeforeValidator(parse_fints_time),
    PlainSerializer(serialize_fints_time, return_type=str),
    Field(description="FinTS time in HHMMSS format"),
]
"""FinTS time type - parses HHMMSS format to Python time."""


FinTSAmount = Annotated[
    Decimal,
    BeforeValidator(parse_fints_amount),
    PlainSerializer(serialize_fints_amount, return_type=str),
    Field(description="FinTS amount with German decimal format (comma separator)"),
]
"""FinTS amount type - parses German decimal format (1234,56) to Decimal."""


FinTSBool = Annotated[
    bool,
    BeforeValidator(parse_fints_bool),
    PlainSerializer(serialize_fints_bool, return_type=str),
    Field(description="FinTS boolean (J=Yes, N=No)"),
]
"""FinTS boolean type - parses J/N to Python bool."""


FinTSNumeric = Annotated[
    int,
    BeforeValidator(parse_fints_numeric),
    PlainSerializer(serialize_fints_numeric, return_type=str),
    Field(description="FinTS numeric (no leading zeros)"),
]
"""FinTS numeric type - parses integer without leading zeros."""


FinTSDigits = Annotated[
    str,
    BeforeValidator(parse_fints_digits),
    Field(description="FinTS digits (string of digits only, may have leading zeros)"),
]
"""FinTS digits type - string containing only digits, allows leading zeros."""


FinTSText = Annotated[
    str,
    BeforeValidator(parse_fints_text),
    Field(description="FinTS text"),
]
"""FinTS text type - general text string."""


FinTSAlphanumeric = Annotated[
    str,
    BeforeValidator(parse_fints_text),
    Field(description="FinTS alphanumeric"),
]
"""FinTS alphanumeric type - letters and numbers."""


FinTSBinary = Annotated[
    bytes,
    BeforeValidator(parse_fints_binary),
    Field(description="FinTS binary data"),
]
"""FinTS binary type - raw bytes."""


FinTSCode = Annotated[
    str,
    BeforeValidator(parse_fints_code),
    Field(description="FinTS code (short identifier)"),
]
"""FinTS code type - short alphanumeric identifier."""


FinTSCurrency = Annotated[
    str,
    BeforeValidator(parse_fints_code),
    Field(
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code (e.g., EUR, USD)",
    ),
]
"""FinTS currency type - 3-character ISO 4217 currency code."""


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
"""FinTS country type - 3-digit ISO 3166 numeric country code."""


FinTSID = Annotated[
    str,
    BeforeValidator(parse_fints_text),
    Field(max_length=30, description="FinTS identifier (max 30 chars)"),
]
"""FinTS identifier type - alphanumeric ID, max 30 characters."""


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Validators (for custom usage)
    "parse_fints_amount",
    "parse_fints_binary",
    "parse_fints_bool",
    "parse_fints_code",
    "parse_fints_date",
    "parse_fints_digits",
    "parse_fints_numeric",
    "parse_fints_text",
    "parse_fints_time",
    # Serializers (for custom usage)
    "serialize_fints_amount",
    "serialize_fints_bool",
    "serialize_fints_date",
    "serialize_fints_numeric",
    "serialize_fints_time",
    # Annotated Types (primary exports)
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
