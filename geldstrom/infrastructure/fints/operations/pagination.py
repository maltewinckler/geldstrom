"""Pagination support for FinTS touchdown-based queries.

FinTS uses "touchdown" pagination where responses include a 3040 code
with a pointer to continue fetching more results.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.dialog import Dialog, ProcessedResponse

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    """Result of a paginated fetch operation."""

    items: Sequence[T]
    pages_fetched: int
    has_more: bool = False


class TouchdownPaginator:
    """
    Handles FinTS touchdown paging for multi-page query results.

    Usage:
        paginator = TouchdownPaginator(dialog)
        result = paginator.fetch(
            segment_factory=lambda tp: HKKAZ7(..., touchdown_point=tp),
            response_type="HIKAZ",
            extract_items=lambda seg: seg.statement_booked,
        )
    """

    CONTINUE_CODE = "3040"  # "More data available" response code

    def __init__(self, dialog: Dialog, max_pages: int = 100) -> None:
        """
        Initialize paginator.

        Args:
            dialog: Dialog to use for sending segments
            max_pages: Maximum pages to fetch (safety limit)
        """
        self._dialog = dialog
        self._max_pages = max_pages

    def fetch(
        self,
        segment_factory: Callable[[str | None], Any],
        response_type: str,
        extract_items: Callable[[Any], T] | None = None,
        transform_items: Callable[[Sequence[Any]], T] | None = None,
    ) -> PaginatedResult[T]:
        """
        Execute a paginated fetch operation.

        Args:
            segment_factory: Creates request segment, receives touchdown point
            response_type: Type of response segment to look for (e.g., "HIKAZ")
            extract_items: Function to extract items from each response segment
            transform_items: Optional function to transform all collected items

        Returns:
            PaginatedResult with all fetched items
        """
        all_items: list[Any] = []
        touchdown_point: str | None = None
        page = 0

        while page < self._max_pages:
            page += 1

            # Create and send segment
            segment = segment_factory(touchdown_point)
            response = self._dialog.send(segment)

            # Extract items from response segments
            items_on_page = self._extract_from_response(
                response, segment, response_type, extract_items
            )
            all_items.extend(items_on_page)

            # Check for continuation
            touchdown_point = self._get_touchdown_point(response, segment)
            if not touchdown_point:
                break

            logger.info("Fetching page %d...", page + 1)

        has_more = touchdown_point is not None and page >= self._max_pages

        # Apply final transformation if provided
        final_items = transform_items(all_items) if transform_items else all_items

        return PaginatedResult(
            items=final_items,
            pages_fetched=page,
            has_more=has_more,
        )

    def _extract_from_response(
        self,
        response: ProcessedResponse,
        request_segment: Any,
        response_type: str,
        extract_items: Callable[[Any], T] | None,
    ) -> list[Any]:
        """Extract items from response segments."""
        items = []

        if response.raw_response is None:
            return items

        # Find response segments that reference our request
        for seg in response.raw_response.response_segments(
            request_segment, response_type
        ):
            if extract_items:
                item = extract_items(seg)
                if item is not None:
                    items.append(item)
            else:
                items.append(seg)

        return items

    def _get_touchdown_point(
        self, response: ProcessedResponse, request_segment: Any
    ) -> str | None:
        """Extract touchdown point from 3040 response if present."""
        if response.raw_response is None:
            return None

        for resp in response.raw_response.responses(
            request_segment, self.CONTINUE_CODE
        ):
            if resp.parameters:
                return resp.parameters[0]

        return None


def find_highest_supported_version(
    bpd_segments,
    segment_classes: Sequence[type],
) -> type | None:
    """
    Find the highest version of a segment supported by both bank and client.

    Args:
        bpd_segments: BPD segments from ParameterStore
        segment_classes: Segment classes the client supports (e.g., HKSAL5, HKSAL6)

    Returns:
        Highest supported segment class, or None if not supported
    """

    def get_version(cls) -> int:
        """Get version from either legacy or Pydantic segment class."""
        if hasattr(cls, "SEGMENT_VERSION"):
            return cls.SEGMENT_VERSION
        return cls.VERSION

    def get_type(cls) -> str:
        """Get type from either legacy or Pydantic segment class."""
        if hasattr(cls, "SEGMENT_TYPE"):
            return cls.SEGMENT_TYPE
        return cls.TYPE

    # Build version map
    version_map = {get_version(cls): cls for cls in segment_classes}

    # Build parameter segment name (HKSAL -> HISALS)
    first_class = segment_classes[0]
    param_name = f"HI{get_type(first_class)[2:]}S"

    # Find highest version in BPD that we also support
    highest = None
    for seg in bpd_segments.find_segments(param_name):
        if seg.header.version in version_map:
            if highest is None or seg.header.version > highest.header.version:
                highest = seg

    if not highest:
        return None

    return version_map.get(highest.header.version)
