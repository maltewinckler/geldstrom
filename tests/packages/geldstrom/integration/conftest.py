"""Project-wide pytest helpers for integration tests.

This module provides:
- Integration test markers and skip logic
- Explicit live-bank marking for tests that hit real FinTS backends
- Parser warning capture fixtures
- Debug output options
- Strict parsing mode for migration validation
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        help=(
            "Execute integration tests that hit real bank backends "
            "(requires .env credentials)."
        ),
    )
    parser.addoption(
        "--fints-env-file",
        default=".env",
        help="Path to the .env file consumed by integration tests (default: .env).",
    )
    parser.addoption(
        "--fints-strict",
        action="store_true",
        help="Enable strict parsing mode (fail on unknown segments).",
    )
    parser.addoption(
        "--fints-debug",
        action="store_true",
        help="Enable verbose FinTS debug logging.",
    )
    parser.addoption(
        "--fints-save-responses",
        type=str,
        default=None,
        metavar="DIR",
        help="Save raw bank responses to DIR for offline debugging.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: requires live FinTS credentials and TAN approval.",
    )
    config.addinivalue_line(
        "markers",
        "live_bank: hits a real FinTS bank backend and cannot run via testcontainers.",
    )

    # Enable strict parsing if requested
    if config.getoption("--fints-strict", default=False):
        import geldstrom.types

        geldstrom.types.STRICT_PARSING = True
        os.environ["FINTS_STRICT_PARSING"] = "1"

    # Enable debug logging if requested
    if config.getoption("--fints-debug", default=False):
        logging.getLogger("geldstrom").setLevel(logging.DEBUG)
        fints_dialog = "geldstrom.infrastructure.fints.dialog"
        fints_proto = "geldstrom.infrastructure.fints.protocol"
        logging.getLogger(fints_dialog).setLevel(logging.DEBUG)
        logging.getLogger(fints_proto).setLevel(logging.DEBUG)


def pytest_collection_modifyitems(config: pytest.Config, items):
    if config.getoption("--run-integration"):
        return
    skip_marker = pytest.mark.skip(
        reason=(
            "live-bank integration tests disabled "
            "(use --run-integration to enable)"
        ),
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(pytest.mark.live_bank)
            item.add_marker(skip_marker)


# ---------------------------------------------------------------------------
# Parser Log Capture
# ---------------------------------------------------------------------------


class _LogCaptureHandler(logging.Handler):
    """Handler that captures log records into a list."""

    def __init__(self, records: list[logging.LogRecord]):
        super().__init__()
        self.records = records

    def emit(self, record: logging.LogRecord):
        self.records.append(record)


@pytest.fixture
def capture_parser_warnings():
    """Fixture that captures FinTS parser log warnings.

    Usage:
        def test_something(capture_parser_warnings):
            with capture_parser_warnings as collector:
                # ... code that might produce parser warnings ...

            # Check warnings
            assert len(collector.warning_messages) == 0
            # Or get a report
            print(collector.report())
    """

    class LogCollector:
        def __init__(self):
            self.log_records: list[logging.LogRecord] = []
            self._handler: _LogCaptureHandler | None = None
            self._logger: logging.Logger | None = None
            self._old_level: int = logging.NOTSET

        def __enter__(self):
            self.log_records = []
            self._handler = _LogCaptureHandler(self.log_records)
            self._logger = logging.getLogger(
                "geldstrom.infrastructure.fints.protocol.parser"
            )
            self._logger.addHandler(self._handler)
            self._old_level = self._logger.level
            self._logger.setLevel(logging.WARNING)
            return self

        def __exit__(self, *args):
            if self._logger and self._handler:
                self._logger.removeHandler(self._handler)
                self._logger.setLevel(self._old_level)

        @property
        def warning_messages(self) -> list[str]:
            return [
                r.getMessage() for r in self.log_records if r.levelno >= logging.WARNING
            ]

        @property
        def unknown_segments(self) -> list[str]:
            return [
                msg for msg in self.warning_messages if "Unknown segment type" in msg
            ]

        @property
        def parse_errors(self) -> list[str]:
            return [msg for msg in self.warning_messages if "Error parsing" in msg]

        def report(self) -> str:
            if not self.warning_messages:
                return "No parser warnings"
            lines = [f"Parser Warnings ({len(self.warning_messages)}):"]
            for msg in self.warning_messages:
                lines.append(f"  - {msg}")
            return "\n".join(lines)

        def assert_no_warnings(self, msg: str = ""):
            if self.warning_messages:
                pytest.fail(f"{msg}\n{self.report()}")

    return LogCollector()


# ---------------------------------------------------------------------------
# Debug Output Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fints_debug_dir(request: pytest.FixtureRequest, tmp_path: Path) -> Path | None:
    """Returns a directory for saving debug output, or None if not enabled.

    Enable with: pytest --fints-save-responses=./debug_output
    """
    save_dir = request.config.getoption("--fints-save-responses")
    if save_dir:
        path = Path(save_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return tmp_path  # Use tmp_path as fallback


@pytest.fixture
def save_raw_response(fints_debug_dir: Path):
    """Fixture to save raw FinTS responses for debugging.

    Usage:
        def test_something(save_raw_response, connection_helper):
            with connection_helper.connect(None) as ctx:
                save_raw_response("bpd", ctx.parameters.bpd.serialize())
                save_raw_response("upd", ctx.parameters.upd.serialize())
    """

    def _save(name: str, data: bytes, extension: str = "bin"):
        if fints_debug_dir:
            path = fints_debug_dir / f"{name}.{extension}"
            path.write_bytes(data)
            print(f"Saved: {path} ({len(data)} bytes)")

    return _save


# ---------------------------------------------------------------------------
# Strict Mode Context Manager
# ---------------------------------------------------------------------------


@pytest.fixture
def strict_parsing():
    """Temporarily enable strict parsing mode.

    Usage:
        def test_strict(strict_parsing):
            with strict_parsing:
                # Parser errors will raise exceptions here
                SegmentSequence(raw_bytes)  # Raises on unknown segments
    """
    import geldstrom.types

    class StrictParsingContext:
        def __init__(self):
            self._original = None

        def __enter__(self):
            self._original = geldstrom.types.STRICT_PARSING
            geldstrom.types.STRICT_PARSING = True
            return self

        def __exit__(self, *args):
            geldstrom.types.STRICT_PARSING = self._original

    return StrictParsingContext()
