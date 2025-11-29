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

from typing import Any, ClassVar, Iterator, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from .types import FinTSAlphanumeric, FinTSNumeric

T = TypeVar("T", bound="FinTSModel")


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
        """
        if data is None:
            data = []

        field_names = list(cls.model_fields.keys())
        kwargs: dict[str, Any] = {}

        for i, value in enumerate(data):
            if i < len(field_names):
                field_name = field_names[i]
                field_info = cls.model_fields[field_name]

                # Handle nested FinTSModel types
                annotation = field_info.annotation
                if isinstance(value, list) and _is_fints_model_type(annotation):
                    # Recursively parse nested model
                    model_type = _extract_model_type(annotation)
                    if model_type is not None:
                        value = model_type.from_wire_list(value)

                # Only set non-None values (let defaults handle missing optional fields)
                if value is not None:
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

        for name in self.__class__.model_fields.keys():
            value = getattr(self, name)

            # Handle nested FinTSModel
            if isinstance(value, FinTSModel):
                value = value.to_wire_list()

            result.append(value)

        return result

    def to_wire_dict(self) -> dict[str, Any]:
        """Export model as dictionary with wire format serialization.

        Uses Pydantic's model_dump with custom serializers.

        Returns:
            Dictionary with serialized values
        """
        return self.model_dump(mode="json")


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
    """

    # Class-level metadata (override in subclasses)
    SEGMENT_TYPE: ClassVar[str] = ""
    SEGMENT_VERSION: ClassVar[int] = 0

    # Segment header (always present as first element)
    header: SegmentHeader = Field(description="Segment header")

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

        for i, value in enumerate(remaining_data):
            if i < len(remaining_fields):
                field_name = remaining_fields[i]
                field_info = cls.model_fields[field_name]

                # Handle nested FinTSModel types
                annotation = field_info.annotation
                if isinstance(value, list) and _is_fints_model_type(annotation):
                    model_type = _extract_model_type(annotation)
                    if model_type is not None:
                        value = model_type.from_wire_list(value)

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
        query: str | type[FinTSSegment] | list[str | type[FinTSSegment]] | None = None,
        version: int | list[int] | None = None,
        callback: callable | None = None,
        recurse: bool = True,
    ) -> Iterator[FinTSSegment]:
        """Find segments matching the given criteria.

        Args:
            query: Segment type(s) to match. Can be:
                   - String: matches SEGMENT_TYPE (e.g., "HISAL")
                   - Type: matches by isinstance
                   - List of strings/types: matches any
            version: Segment version(s) to match
            callback: Custom filter function(segment) -> bool
            recurse: Whether to recurse into nested segments

        Yields:
            Matching segments

        Example:
            # Find all balance responses
            for seg in seq.find_segments(query="HISAL"):
                print(seg)

            # Find HISAL version 6 or 7
            for seg in seq.find_segments(query="HISAL", version=[6, 7]):
                print(seg)

            # Custom filter
            for seg in seq.find_segments(callback=lambda s: s.header.number > 5):
                print(seg)
        """
        # Normalize query to list
        if query is None:
            queries: list[str | type] = []
        elif isinstance(query, (str, type)):
            queries = [query]
        else:
            queries = list(query)

        # Normalize version to list
        if version is None:
            versions: list[int] = []
        elif isinstance(version, int):
            versions = [version]
        else:
            versions = list(version)

        for segment in self.segments:
            # Check type match
            if queries:
                type_match = any(
                    (isinstance(segment, q) if isinstance(q, type) else segment.SEGMENT_TYPE == q)
                    for q in queries
                )
                if not type_match:
                    continue

            # Check version match
            if versions and segment.SEGMENT_VERSION not in versions:
                continue

            # Check callback
            if callback is not None and not callback(segment):
                continue

            yield segment

            # Recurse into nested segment sequences if requested
            if recurse:
                for field_name in segment.__class__.model_fields.keys():
                    field_value = getattr(segment, field_name, None)
                    if isinstance(field_value, SegmentSequence):
                        yield from field_value.find_segments(
                            query=query,
                            version=version,
                            callback=callback,
                            recurse=recurse,
                        )

    def find_segment_first(
        self,
        query: str | type[FinTSSegment] | list[str | type[FinTSSegment]] | None = None,
        version: int | list[int] | None = None,
        callback: callable | None = None,
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
            version=version,
            callback=callback,
            recurse=recurse,
        ):
            return segment
        return None

    def find_segment_highest_version(
        self,
        query: str | type[FinTSSegment] | list[str | type[FinTSSegment]] | None = None,
        version: int | list[int] | None = None,
        callback: callable | None = None,
        recurse: bool = True,
        default: FinTSSegment | None = None,
    ) -> FinTSSegment | None:
        """Find the segment with the highest version matching criteria.

        Args:
            query: Segment type(s) to match
            version: Version(s) to filter by
            callback: Custom filter function
            recurse: Whether to recurse into nested segments
            default: Value to return if no match found

        Returns:
            Segment with highest version, or default if not found
        """
        highest: FinTSSegment | None = None

        for segment in self.find_segments(
            query=query,
            version=version,
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


__all__ = [
    "FinTSModel",
    "FinTSDataElementGroup",
    "FinTSSegment",
    "SegmentHeader",
    "SegmentSequence",
]

