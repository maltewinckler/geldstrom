"""FinTS Protocol Base Models.

This module provides base classes for all FinTS protocol models:
- FinTSModel: Base for all protocol models
- FinTSDataElementGroup: Base for Data Element Groups (DEGs)
- FinTSSegment: Base for FinTS segments
- SegmentHeader: Common segment header
- SegmentSequence: Collection of segments with query methods

These base classes provide:
1. Common configuration for all protocol models
2. Wire format parsing via from_wire_list()
3. Wire format serialization via to_wire_list()
4. Segment discovery via find_segments()
"""

from __future__ import annotations

import logging
import types
from collections.abc import Callable, Iterator
from typing import Any, ClassVar, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .types import FinTSAlphanumeric, FinTSNumeric

T = TypeVar("T", bound="FinTSModel")

logger = logging.getLogger(__name__)


def _is_string_type(annotation: Any) -> bool:
    """Check if annotation is a string type.

    Used to determine if None should be converted to empty string.
    """
    if annotation is str:
        return True
    # Check for annotated types like FinTSAlphanumeric
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        return False
    # Check if it's a NewType or Annotated wrapping str
    if hasattr(annotation, "__supertype__"):
        return annotation.__supertype__ is str
    return False


def _unwrap_optional(annotation: Any) -> tuple[Any, Any]:
    """Unwrap Optional[X] or X | None to get the actual type.

    Returns:
        (actual_type, origin) where origin is the __origin__ of actual_type
    """
    origin = getattr(annotation, "__origin__", None)
    if origin is Union or isinstance(annotation, types.UnionType):
        for arg in getattr(annotation, "__args__", ()):
            if arg is not type(None):
                return arg, getattr(arg, "__origin__", None)
    return annotation, origin


def _get_list_inner_type(annotation: Any) -> Any | None:
    """Extract the inner type from a list annotation.

    Handles list[X], list[Optional[X]], etc.
    Returns None if not a valid list type.
    """
    args = getattr(annotation, "__args__", ())
    if not args:
        return None

    inner_type = args[0]

    # Handle Optional inner type: list[Optional[X]] -> X
    if getattr(inner_type, "__origin__", None) is type(None):
        return None  # Optional list with None

    inner_args = getattr(inner_type, "__args__", ())
    if inner_args and type(None) in inner_args:
        for arg in inner_args:
            if arg is not type(None):
                return arg
    return inner_type


def _parse_list_of_degs(
    inner_type: type,
    data: list[Any],
    data_index: int,
    cls_name: str,
    field_name: str,
) -> tuple[list[Any], int]:
    """Parse a list of DEGs from wire data.

    Some banks send fewer fields than the model defines (e.g., omitting optional
    fields). This function tries to detect DEG boundaries by:
    1. Using the expected field count as a starting point
    2. If parsing fails, looking for the next element that looks like a new DEG
       (e.g., a 3-digit code for TwoStepParameters)

    Returns:
        (parsed_items, new_data_index)
    """
    inner_field_count = _count_model_fields(inner_type)
    list_values = []
    remaining_data = data[data_index:]

    chunk_start = 0
    while chunk_start < len(remaining_data):
        # Try standard chunk size first
        chunk = remaining_data[chunk_start : chunk_start + inner_field_count]
        if len(chunk) == 0:
            break

        try:
            item = inner_type.from_wire_list(chunk)
            list_values.append(item)
            chunk_start += inner_field_count
        except Exception:
            # Parsing failed - try to find actual DEG boundary
            # Look for the next element that could start a new DEG
            # (typically a 2-3 digit code for security_function)
            actual_end = _find_deg_boundary(
                remaining_data, chunk_start, inner_field_count
            )
            if actual_end > chunk_start:
                # Try parsing with the detected boundary
                smaller_chunk = remaining_data[chunk_start:actual_end]
                try:
                    item = inner_type.from_wire_list(smaller_chunk)
                    list_values.append(item)
                    chunk_start = actual_end
                    continue
                except Exception as exc:
                    logger.warning(
                        "Failed to parse list field %s.%s chunk %s: %s",
                        cls_name,
                        field_name,
                        smaller_chunk,
                        exc,
                    )
                    break
            else:
                # No boundary found, give up
                logger.warning(
                    "Failed to parse list field %s.%s chunk %s",
                    cls_name,
                    field_name,
                    chunk,
                )
                break

    return list_values, len(data)


def _find_deg_boundary(data: list[Any], start: int, expected_size: int) -> int:
    """Find the actual end of a DEG in the data.

    Looks for patterns that indicate the start of a new DEG:
    - A 2-3 digit numeric code (typical security_function)
    - After at least half the expected fields

    Returns:
        Index of the boundary, or start + expected_size if not found
    """
    min_fields = expected_size // 2  # At least half the expected fields

    for i in range(start + min_fields, min(start + expected_size, len(data))):
        value = data[i]
        # Check if this looks like a security_function (start of new DEG)
        if (
            value is not None
            and isinstance(value, str)
            and len(value) <= 3
            and value.isdigit()
            and int(value) >= 100  # Typical security_function codes are 900+
        ):
            return i

    return start + expected_size


def _parse_nested_model(
    model_type: type,
    value: Any,
    data: list[Any],
    data_index: int,
) -> tuple[Any, int]:
    """Parse a nested FinTSModel from wire data.

    Handles both structured (value is list) and flat data.

    Returns:
        (parsed_value, new_data_index)
    """
    if isinstance(value, list):
        # Already structured - use as-is
        return model_type.from_wire_list(value), data_index + 1

    # Flat data - consume multiple elements
    nested_field_count = _count_model_fields(model_type)
    nested_data = data[data_index : data_index + nested_field_count]
    return model_type.from_wire_list(nested_data), data_index + nested_field_count


def _is_optional_type(annotation: Any) -> bool:
    """Check if annotation is Optional[X] or X | None."""
    origin = getattr(annotation, "__origin__", None)
    if origin is type(None):
        return True
    if origin is Union or isinstance(annotation, types.UnionType):
        return type(None) in getattr(annotation, "__args__", ())
    return False


class FinTSModel(BaseModel):
    """Base class for all FinTS protocol models.

    This class provides:
    - Common Pydantic configuration for FinTS models
    - Wire format parsing via from_wire_list()
    - Wire format serialization via to_wire_list()

    Example:
        class Amount(FinTSModel):
            value: FinTSAmount
            currency: FinTSCurrency

        # Parse from wire format
        amount = Amount.from_wire_list(["1234,56", "EUR"])

        # Serialize to wire format
        wire_data = amount.to_wire_list()
    """

    model_config = ConfigDict(
        # Allow coercion via validators (e.g., "20231225" → date)
        strict=False,
        # Ignore unknown fields from bank responses
        extra="ignore",
        # Allow population by field name
        populate_by_name=True,
        # Validate default values
        validate_default=True,
        # Use enum values for serialization
        use_enum_values=True,
    )

    @classmethod
    def from_wire_list(cls: type[T], data: list[Any] | None) -> T:
        """Parse model from FinTS DEG/segment data list.

        This method maps positional data from the wire format to model fields
        in the order they are defined in the model.

        Handles both:
        - Structured data: nested lists for nested DEGs (e.g., [['280', '12345'], 'user'])
        - Flat data: all elements in a single list (e.g., ['280', '12345', 'user'])

        Args:
            data: List of values in field definition order, or None

        Returns:
            New model instance

        Raises:
            ValueError: If required fields are missing

        Example:
            class BankId(FinTSModel):
                country: FinTSCountry
                bank_code: FinTSAlphanumeric

            bank = BankId.from_wire_list(["280", "12345678"])
            assert bank.country == "280"
            assert bank.bank_code == "12345678"
        """  # NOQA: E501
        if data is None:
            data = []

        kwargs: dict[str, Any] = {}
        data_index = 0

        for field_name, field_info in cls.model_fields.items():
            if data_index >= len(data):
                break

            annotation = field_info.annotation
            actual_annotation, origin = _unwrap_optional(annotation)

            # Handle list fields (consume all remaining data)
            if origin is list:
                inner_type = _get_list_inner_type(actual_annotation)
                if inner_type is None:
                    continue

                if hasattr(inner_type, "from_wire_list"):
                    # list[DEG] - parse in chunks
                    list_values, data_index = _parse_list_of_degs(
                        inner_type, data, data_index, cls.__name__, field_name
                    )
                    if list_values:
                        kwargs[field_name] = list_values
                else:
                    # list[primitive] - collect remaining
                    remaining = data[data_index:]
                    if remaining:
                        kwargs[field_name] = list(remaining)
                    data_index = len(data)
                continue

            value = data[data_index]

            # Handle nested FinTSModel types
            if _is_fints_model_type(annotation):
                model_type = _extract_model_type(annotation)
                if model_type is not None:
                    value, data_index = _parse_nested_model(
                        model_type, value, data, data_index
                    )
                else:
                    data_index += 1
            else:
                data_index += 1

            # Handle None values based on field type
            if value is None:
                if _is_optional_type(annotation):
                    continue  # Let defaults handle it
                if _is_string_type(annotation):
                    kwargs[field_name] = ""  # Required string → empty
            else:
                kwargs[field_name] = value

        return cls(**kwargs)

    def to_wire_list(self) -> list[Any]:
        """Export model as FinTS DEG/segment data list.

        This method serializes model fields to a list suitable for
        FinTS wire format encoding.

        Returns:
            List of serialized values in field definition order

        Example:
            amount = Amount(value=Decimal("1234.56"), currency="EUR")
            wire = amount.to_wire_list()
            assert wire == ["1234,56", "EUR"]
        """
        result: list[Any] = []

        for name in self.__class__.model_fields:
            value = getattr(self, name)

            # Handle nested FinTSModel
            if isinstance(value, FinTSModel):
                value = value.to_wire_list()
            elif isinstance(value, list):
                # Check if this is a list of FinTSModels (repeating DEGs)
                # or a list of simple values (repeating data elements)
                if value and isinstance(value[0], FinTSModel):
                    # List of DEGs - each becomes a separate wire list
                    for item in value:
                        result.append(item.to_wire_list())
                else:
                    # List of simple values - add each as separate element
                    # (repeating data elements within DEG)
                    for item in value:
                        result.append(item)
                continue  # Skip the append below

            result.append(value)

        return result


class FinTSDataElementGroup(FinTSModel):
    """Base class for FinTS Data Element Groups (DEGs).

    DEGs are structured groups of data elements that appear within
    segments. Examples: BankIdentifier, Balance, Amount.

    This class is a semantic marker - it has the same functionality
    as FinTSModel but indicates the object is a DEG.

    Example:
        class BankIdentifier(FinTSDataElementGroup):
            country_identifier: FinTSCountry
            bank_code: FinTSAlphanumeric
    """

    pass


class SegmentHeader(FinTSDataElementGroup):
    """FinTS Segment Header (Segmentkopf).

    Every FinTS segment starts with a header containing:
    - type: Segment type identifier (e.g., "HISAL", "HKSAL")
    - number: Segment number within the message
    - version: Segment version number
    - reference: Optional reference to another segment

    Example:
        header = SegmentHeader.from_wire_list(["HISAL", "5", "6", "3"])
        assert header.type == "HISAL"
        assert header.number == 5
        assert header.version == 6
        assert header.reference == 3
    """

    type: FinTSAlphanumeric = Field(
        max_length=6,
        description="Segment type identifier (Segmentkennung)",
    )
    number: FinTSNumeric = Field(
        description="Segment number within message (Segmentnummer)",
    )
    version: FinTSNumeric = Field(
        description="Segment version (Segmentversion)",
    )
    reference: FinTSNumeric | None = Field(
        default=None,
        description="Reference to another segment (Bezugssegment)",
    )


class FinTSSegment(FinTSModel):
    """Base class for FinTS Segments.

    Segments are the main building blocks of FinTS messages.
    Each segment has:
    - A header with type, number, version
    - Segment-specific data fields

    Subclasses should define:
    - SEGMENT_TYPE: The segment type identifier (e.g., "HISAL")
    - SEGMENT_VERSION: The segment version number

    Example:
        class HISAL6(FinTSSegment):
            SEGMENT_TYPE = "HISAL"
            SEGMENT_VERSION = 6

            account: AccountIdentifier
            balance_booked: Balance
            # ... more fields

    Segments can be instantiated with just the data fields - the header
    will be auto-generated from SEGMENT_TYPE and SEGMENT_VERSION:

        # Auto-header generation
        seg = HKIDN2(
            bank_identifier=bank_id,
            customer_id="customer123",
            system_id="0",
            system_id_status=SystemIDStatus.ID_NECESSARY,
        )
        # seg.header is auto-generated with type="HKIDN", version=2, number=0

    Auto-Registration:
        Segment classes are automatically registered when defined.
        Use FinTSSegment.get_segment_class(type, version) to look up.
    """

    # Class-level metadata (override in subclasses)
    SEGMENT_TYPE: ClassVar[str] = ""
    SEGMENT_VERSION: ClassVar[int] = 0

    # Auto-registration registry: (type, version) -> class
    _segment_registry: ClassVar[dict[tuple[str, int], type[FinTSSegment]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-register segment subclasses."""
        super().__init_subclass__(**kwargs)
        # Only register if both type and version are set (not base classes)
        if cls.SEGMENT_TYPE and cls.SEGMENT_VERSION:
            key = (cls.SEGMENT_TYPE, cls.SEGMENT_VERSION)
            FinTSSegment._segment_registry[key] = cls

    @classmethod
    def get_segment_class(
        cls, segment_type: str, version: int
    ) -> type[FinTSSegment] | None:
        """Look up a segment class by type and version."""
        return cls._segment_registry.get((segment_type, version))

    @classmethod
    def get_registered_types(cls) -> set[str]:
        """Get all registered segment types."""
        return {t for t, _ in cls._segment_registry}

    @classmethod
    def get_versions(cls, segment_type: str) -> list[int]:
        """Get all registered versions for a segment type."""
        return sorted(v for t, v in cls._segment_registry if t == segment_type)

    # Segment header (always present as first element)
    header: SegmentHeader = Field(description="Segment header")

    @model_validator(mode="before")
    @classmethod
    def _auto_generate_header(cls, data: Any) -> Any:
        """Auto-generate header if not provided.

        This allows segments to be instantiated with just data fields:
            HKIDN2(bank_identifier=..., customer_id=..., ...)

        Instead of requiring explicit header:
            HKIDN2(header=SegmentHeader(...), bank_identifier=..., ...)
        """
        if isinstance(data, dict) and ("header" not in data or data["header"] is None):
            # Get segment type/version from class
            segment_type = getattr(cls, "SEGMENT_TYPE", "")
            segment_version = getattr(cls, "SEGMENT_VERSION", 0)

            if segment_type and segment_version:
                data["header"] = SegmentHeader(
                    type=segment_type,
                    number=0,  # Will be set by message builder
                    version=segment_version,
                    reference=None,
                )
        return data

    @classmethod
    def segment_id(cls) -> str:
        """Get segment identifier (type + version).

        Returns:
            Segment ID like "HISAL6"
        """
        return f"{cls.SEGMENT_TYPE}{cls.SEGMENT_VERSION}"

    @classmethod
    def from_wire_list(cls: type[T], data: list[Any] | None) -> T:
        """Parse segment from FinTS wire format.

        The first element is always the header, followed by segment data.
        Handles both structured data (nested lists) and flat data.

        Args:
            data: List starting with header, then segment fields

        Returns:
            Parsed segment instance
        """
        if data is None or len(data) == 0:
            raise ValueError("Segment data cannot be empty")

        # Parse header from first element
        header_data = data[0]
        if isinstance(header_data, list):
            header = SegmentHeader.from_wire_list(header_data)
        elif isinstance(header_data, SegmentHeader):
            header = header_data
        else:
            raise ValueError(f"Invalid header data: {header_data}")

        # Parse remaining fields
        field_names = list(cls.model_fields.keys())
        kwargs: dict[str, Any] = {"header": header}

        # Skip first field (header) in iteration
        remaining_fields = field_names[1:]
        remaining_data = data[1:]
        data_index = 0

        for field_name in remaining_fields:
            if data_index >= len(remaining_data):
                break

            field_info = cls.model_fields[field_name]
            annotation = field_info.annotation
            value = remaining_data[data_index]

            # Handle nested FinTSModel types
            if _is_fints_model_type(annotation):
                model_type = _extract_model_type(annotation)
                if model_type is not None:
                    if isinstance(value, list):
                        # Already structured - use as-is
                        value = model_type.from_wire_list(value)
                        data_index += 1
                    else:
                        # Flat data - consume multiple elements for nested model
                        nested_field_count = _count_model_fields(model_type)
                        nested_data = remaining_data[
                            data_index : data_index + nested_field_count
                        ]
                        value = model_type.from_wire_list(nested_data)
                        data_index += nested_field_count
                else:
                    data_index += 1
            else:
                data_index += 1

            if value is not None:
                kwargs[field_name] = value

        return cls(**kwargs)


class SegmentSequence(FinTSModel):
    """Collection of FinTS segments with query methods.

    This class provides functionality to:
    - Store a list of segments
    - Find segments by type, version, or custom criteria
    - Parse from/serialize to wire format

    Example:
        seq = SegmentSequence(segments=[seg1, seg2, seg3])

        # Find all HISAL segments
        for seg in seq.find_segments(query="HISAL"):
            print(seg.balance_booked)

        # Find first HIBPA segment
        bpa = seq.find_segment_first(query="HIBPA")

        # Find highest version of HKSAL
        highest = seq.find_segment_highest_version(query="HKSAL")
    """

    segments: list[FinTSSegment] = Field(default_factory=list)

    def find_segments(
        self,
        query: str | type[FinTSSegment] | None = None,
        callback: Callable[[FinTSSegment], bool] | None = None,
        recurse: bool = True,
    ) -> Iterator[FinTSSegment]:
        """Find segments matching the given criteria.

        Args:
            query: Segment type to match. Can be:
                   - String: matches SEGMENT_TYPE (e.g., "HISAL")
                   - Type: matches by isinstance
            callback: Custom filter function(segment) -> bool
            recurse: Whether to recurse into nested segments

        Yields:
            Matching segments

        Example:
            # Find all balance responses
            for seg in seq.find_segments(query="HISAL"):
                print(seg)

            # Custom filter
            for seg in seq.find_segments(callback=lambda s: s.header.number > 5):
                print(seg)
        """
        for segment in self.segments:
            # Check if this segment matches the criteria
            matches = True

            # Check type match
            if query is not None:
                if isinstance(query, type):
                    matches = isinstance(segment, query)
                else:
                    # Check both class SEGMENT_TYPE and header.type
                    # (header.type is needed for GenericSegment fallbacks)
                    matches = (
                        query == segment.SEGMENT_TYPE or query == segment.header.type
                    )

            # Check callback
            if matches and callback is not None:
                matches = callback(segment)

            # Yield the segment if it matches
            if matches:
                yield segment

            # Recurse into nested segment sequences REGARDLESS of match
            # (we need to find nested segments that match even if the container doesn't)
            if recurse:
                # Check model fields for nested SegmentSequence
                for field_name in segment.__class__.model_fields:
                    field_value = getattr(segment, field_name, None)
                    if isinstance(field_value, SegmentSequence):
                        yield from field_value.find_segments(
                            query=query,
                            callback=callback,
                            recurse=recurse,
                        )

                # Also check for 'segments' property (used by HNVSD1 for encrypted data)
                if (
                    hasattr(segment, "segments")
                    and "segments" not in segment.__class__.model_fields
                ):
                    nested = getattr(segment, "segments", None)
                    if isinstance(nested, SegmentSequence):
                        yield from nested.find_segments(
                            query=query,
                            callback=callback,
                            recurse=recurse,
                        )

    def find_segment_first(
        self,
        query: str | type[FinTSSegment] | None = None,
        callback: Callable[[FinTSSegment], bool] | None = None,
        recurse: bool = True,
    ) -> FinTSSegment | None:
        """Find the first segment matching the criteria.

        Args:
            Same as find_segments()

        Returns:
            First matching segment, or None if not found
        """
        for segment in self.find_segments(
            query=query,
            callback=callback,
            recurse=recurse,
        ):
            return segment
        return None

    def find_segment_highest_version(
        self,
        query: str | type[FinTSSegment] | None = None,
        callback: Callable[[FinTSSegment], bool] | None = None,
        recurse: bool = True,
        default: FinTSSegment | None = None,
    ) -> FinTSSegment | None:
        """Find the segment with the highest version matching criteria.

        Args:
            query: Segment type to match
            callback: Custom filter function
            recurse: Whether to recurse into nested segments
            default: Value to return if no match found

        Returns:
            Segment with highest version, or default if not found
        """
        highest: FinTSSegment | None = None

        for segment in self.find_segments(
            query=query,
            callback=callback,
            recurse=recurse,
        ):
            if highest is None or segment.SEGMENT_VERSION > highest.SEGMENT_VERSION:
                highest = segment

        return highest if highest is not None else default

    def __iter__(self) -> Iterator[FinTSSegment]:
        """Iterate over segments."""
        return iter(self.segments)

    def __len__(self) -> int:
        """Return number of segments."""
        return len(self.segments)

    def print_nested(
        self,
        stream=None,
        level: int = 0,
        indent: str = "    ",
        prefix: str = "",
        first_level_indent: bool = True,
        trailer: str = "",
        print_doc: bool = True,
        first_line_suffix: str = "",
    ) -> None:
        """Print a human-readable representation of the segment sequence.

        Args:
            stream: Output stream (defaults to sys.stdout)
            level: Current indentation level
            indent: Indentation string per level
            prefix: Prefix for each line
            first_level_indent: Whether to indent the first line
            trailer: Suffix for the last line
            print_doc: Whether to include docstrings
            first_line_suffix: Suffix for the first line
        """
        import sys

        stream = stream or sys.stdout
        stream.write(
            ((prefix + level * indent) if first_level_indent else "")
            + f"{self.__class__.__module__}.{self.__class__.__name__}(["
            + first_line_suffix
            + "\n"
        )
        for segment in self.segments:
            docstring = ""
            if print_doc and segment.__doc__:
                docstring = segment.__doc__.splitlines()[0].strip()
                if docstring:
                    docstring = f" # {docstring}"

            # Check if segment has print_nested method
            if hasattr(segment, "print_nested"):
                segment.print_nested(
                    stream=stream,
                    level=level + 1,
                    indent=indent,
                    prefix=prefix,
                    trailer="," + docstring,
                    print_doc=print_doc,
                )
            else:
                # Fallback for segments without print_nested
                stream.write(f"{prefix}{(level + 1) * indent}{segment!r},{docstring}\n")
        stream.write(f"{prefix}{level * indent}]){trailer}\n")

    # =========================================================================
    # Serialization Methods (Phase 1 additions)
    # =========================================================================

    def render_bytes(self) -> bytes:
        """Serialize all segments to FinTS wire format.

        Returns:
            Raw bytes in FinTS wire format, ready to send to a bank.

        Example:
            seq = SegmentSequence(segments=[seg1, seg2])
            raw = seq.render_bytes()
            # raw is now b"HNHBK:1:3+...'"
        """
        from .parser import FinTSSerializer

        serializer = FinTSSerializer()
        serialized_segments = [
            serializer.serialize_segment(segment) for segment in self.segments
        ]
        return serializer.implode_segments(serialized_segments)

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        robust_mode: bool = True,
    ) -> SegmentSequence:
        """Parse a FinTS message from raw bytes.

        Args:
            data: Raw bytes from bank response
            robust_mode: If True (default), unknown segments become warnings.
                        If False, unknown segments raise exceptions.

        Returns:
            SegmentSequence containing parsed segments

        Example:
            raw = b"HNHBK:1:3+...'"
            seq = SegmentSequence.from_bytes(raw)
            for seg in seq.find_segments(query="HISAL"):
                print(seg)
        """
        from .parser import FinTSParser

        parser = FinTSParser(robust_mode=robust_mode)
        result = parser.parse_message(data)
        return cls(segments=list(result.segments))

    def __init__(self, segments: list[FinTSSegment] | bytes | None = None, **kwargs):
        """Initialize a SegmentSequence.

        Args:
            segments: Either a list of segment objects, or raw bytes to parse.
                     If bytes, uses the Pydantic parser.
            **kwargs: Additional Pydantic model arguments.

        Example:
            # From segment list
            seq = SegmentSequence(segments=[seg1, seg2])

            # From raw bytes (parses automatically)
            seq = SegmentSequence(b"HNHBK:1:3+...'")
        """
        if isinstance(segments, bytes):
            # Parse bytes using Pydantic parser
            parsed = self.from_bytes(segments)
            super().__init__(segments=parsed.segments, **kwargs)
        else:
            super().__init__(segments=segments or [], **kwargs)


# =============================================================================
# Helper Functions
# =============================================================================


def _is_fints_model_type(annotation: Any) -> bool:
    """Check if annotation is or contains a FinTSModel type."""
    if annotation is None:
        return False

    # Handle direct type
    if isinstance(annotation, type) and issubclass(annotation, FinTSModel):
        return True

    # Handle Optional[T], Union[T, None], etc.
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        args = getattr(annotation, "__args__", ())
        return any(_is_fints_model_type(arg) for arg in args)

    return False


def _extract_model_type(annotation: Any) -> type[FinTSModel] | None:
    """Extract FinTSModel type from annotation."""
    if annotation is None:
        return None

    # Handle direct type
    if isinstance(annotation, type) and issubclass(annotation, FinTSModel):
        return annotation

    # Handle Optional[T], Union[T, None], etc.
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        args = getattr(annotation, "__args__", ())
        for arg in args:
            result = _extract_model_type(arg)
            if result is not None:
                return result

    return None


def _count_model_fields(model_type: type[FinTSModel]) -> int:
    """Count total wire elements a model consumes, including nested models.

    This recursively counts fields, expanding nested FinTSModel types
    to their full field count.

    Args:
        model_type: The model type to count fields for

    Returns:
        Total number of wire elements consumed by this model
    """
    count = 0
    for field_info in model_type.model_fields.values():
        annotation = field_info.annotation
        nested_type = _extract_model_type(annotation)
        if nested_type is not None:
            # Recursively count nested model fields
            count += _count_model_fields(nested_type)
        else:
            count += 1
    return count


__all__ = [
    "FinTSModel",
    "FinTSDataElementGroup",
    "FinTSSegment",
    "SegmentHeader",
    "SegmentSequence",
]
