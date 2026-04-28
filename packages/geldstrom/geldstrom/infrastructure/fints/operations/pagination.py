"""Pagination support for FinTS touchdown-based queries.

FinTS uses "touchdown" pagination where responses include a 3040 code
with a pointer to continue fetching more results.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.dialog import Dialog, ProcessedResponse

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):  # noqa: UP046
    """Result of a paginated fetch operation."""

    items: Sequence[T]
    pages_fetched: int
    has_more: bool = False


class TouchdownPaginator:
    """Handles FinTS touchdown paging for multi-page query results."""

    CONTINUE_CODE = "3040"  # "More data available" response code

    def __init__(self, dialog: Dialog, max_pages: int = 100) -> None:
        self._dialog = dialog
        self._max_pages = max_pages

    def fetch(
        self,
        segment_factory: Callable[[str | None], Any],
        response_type: str,
        extract_items: Callable[[Any], T] | None = None,
        transform_items: Callable[[Sequence[Any]], T] | None = None,
    ) -> PaginatedResult[T]:
        """Execute a paginated fetch operation."""
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
        if response.raw_response is None:
            return None

        for resp in response.raw_response.responses(
            request_segment, self.CONTINUE_CODE
        ):
            if resp.parameters:
                return resp.parameters[0]

        return None
