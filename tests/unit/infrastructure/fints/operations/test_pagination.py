"""Tests for the pagination module."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fints.infrastructure.fints.operations.pagination import (
    PaginatedResult,
    TouchdownPaginator,
    find_highest_supported_version,
)


class TestPaginatedResult:
    """Tests for PaginatedResult dataclass."""

    def test_basic_result(self):
        """PaginatedResult should store items and metadata."""
        result = PaginatedResult(
            items=["a", "b", "c"],
            pages_fetched=2,
            has_more=False,
        )
        assert result.items == ["a", "b", "c"]
        assert result.pages_fetched == 2
        assert result.has_more is False

    def test_default_has_more(self):
        """has_more should default to False."""
        result = PaginatedResult(items=[], pages_fetched=1)
        assert result.has_more is False


class TestTouchdownPaginator:
    """Tests for TouchdownPaginator class."""

    @pytest.fixture
    def mock_dialog(self):
        """Create a mock dialog."""
        return MagicMock()

    def test_single_page_fetch(self, mock_dialog):
        """Paginator should handle single page results."""
        # Setup mock response without continuation
        mock_response = MagicMock()
        mock_response.raw_response = MagicMock()
        mock_response.raw_response.response_segments.return_value = [
            MagicMock(data="item1"),
            MagicMock(data="item2"),
        ]
        mock_response.raw_response.responses.return_value = []  # No 3040 code

        mock_dialog.send.return_value = mock_response

        paginator = TouchdownPaginator(mock_dialog)
        result = paginator.fetch(
            segment_factory=lambda tp: MagicMock(),
            response_type="TESTTYPE",
        )

        assert result.pages_fetched == 1
        assert result.has_more is False
        mock_dialog.send.assert_called_once()

    def test_extracts_touchdown_point(self, mock_dialog):
        """Paginator should extract touchdown point from 3040 response."""
        # First page with continuation
        page1_response = MagicMock()
        page1_response.raw_response = MagicMock()
        page1_response.raw_response.response_segments.return_value = [MagicMock()]
        page1_response.raw_response.responses.return_value = [
            MagicMock(parameters=["touchdown123"])
        ]

        # Second page without continuation
        page2_response = MagicMock()
        page2_response.raw_response = MagicMock()
        page2_response.raw_response.response_segments.return_value = [MagicMock()]
        page2_response.raw_response.responses.return_value = []

        mock_dialog.send.side_effect = [page1_response, page2_response]

        segment_factory = MagicMock(return_value=MagicMock())

        paginator = TouchdownPaginator(mock_dialog)
        result = paginator.fetch(
            segment_factory=segment_factory,
            response_type="TEST",
        )

        assert result.pages_fetched == 2
        # Second call should have touchdown point
        assert segment_factory.call_count == 2
        segment_factory.assert_any_call(None)  # First call
        segment_factory.assert_any_call("touchdown123")  # Second call

    def test_respects_max_pages(self, mock_dialog):
        """Paginator should stop at max_pages even with more data."""
        # Always return continuation
        mock_response = MagicMock()
        mock_response.raw_response = MagicMock()
        mock_response.raw_response.response_segments.return_value = [MagicMock()]
        mock_response.raw_response.responses.return_value = [
            MagicMock(parameters=["more"])
        ]

        mock_dialog.send.return_value = mock_response

        paginator = TouchdownPaginator(mock_dialog, max_pages=3)
        result = paginator.fetch(
            segment_factory=lambda tp: MagicMock(),
            response_type="TEST",
        )

        assert result.pages_fetched == 3
        assert result.has_more is True

    def test_handles_null_raw_response(self, mock_dialog):
        """Paginator should handle missing raw_response."""
        mock_response = MagicMock()
        mock_response.raw_response = None

        mock_dialog.send.return_value = mock_response

        paginator = TouchdownPaginator(mock_dialog)
        result = paginator.fetch(
            segment_factory=lambda tp: MagicMock(),
            response_type="TEST",
        )

        assert result.items == []
        assert result.pages_fetched == 1


class TestFindHighestSupportedVersion:
    """Tests for find_highest_supported_version function."""

    def test_finds_highest_version(self):
        """Should return highest matching version."""
        # Mock segment classes
        class MockV5:
            TYPE = "HKSAL"
            VERSION = 5

        class MockV6:
            TYPE = "HKSAL"
            VERSION = 6

        class MockV7:
            TYPE = "HKSAL"
            VERSION = 7

        # Mock BPD segments that support version 6
        mock_bpd = MagicMock()
        mock_highest = MagicMock()
        mock_highest.header.version = 6
        mock_bpd.find_segment_highest_version.return_value = mock_highest

        result = find_highest_supported_version(mock_bpd, [MockV7, MockV6, MockV5])

        assert result == MockV6

    def test_returns_none_if_not_supported(self):
        """Should return None if bank doesn't support operation."""
        class MockV5:
            TYPE = "HKSAL"
            VERSION = 5

        mock_bpd = MagicMock()
        mock_bpd.find_segment_highest_version.return_value = None

        result = find_highest_supported_version(mock_bpd, [MockV5])

        assert result is None

