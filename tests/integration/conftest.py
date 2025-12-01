"""Project-wide pytest helpers for integration tests.

This module provides:
- Integration test markers and skip logic
- Parser warning capture fixtures
- Debug output options
- Strict parsing mode for migration validation
"""
from __future__ import annotations

import logging
import os
import warnings
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

    # Enable strict parsing if requested
    if config.getoption("--fints-strict", default=False):
        import geldstrom.types
        geldstrom.types.STRICT_PARSING = True
        os.environ["FINTS_STRICT_PARSING"] = "1"

    # Enable debug logging if requested
    if config.getoption("--fints-debug", default=False):
        logging.getLogger("geldstrom").setLevel(logging.DEBUG)
        logging.getLogger("geldstrom.infrastructure.fints.dialog").setLevel(logging.DEBUG)
        logging.getLogger("geldstrom.infrastructure.fints.protocol").setLevel(logging.DEBUG)


def pytest_collection_modifyitems(config: pytest.Config, items):
    if config.getoption("--run-integration"):
        return
    skip_marker = pytest.mark.skip(
        reason="integration tests disabled (use --run-integration to enable)",
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_marker)


# ---------------------------------------------------------------------------
# Parser Warning Capture
# ---------------------------------------------------------------------------


@pytest.fixture
def capture_parser_warnings():
    """Fixture that captures FinTS parser warnings.

    Usage:
        def test_something(capture_parser_warnings):
            with capture_parser_warnings as collector:
                # ... code that might produce parser warnings ...

            # Check warnings
            assert len(collector.warnings) == 0
            # Or get a report
            print(collector.report())
    """
    from geldstrom.infrastructure.fints.protocol.parser import FinTSParserWarning

    class WarningCollector:
        def __init__(self):
            self.warnings: list[warnings.WarningMessage] = []
            self._context = None

        def __enter__(self):
            self._context = warnings.catch_warnings(record=True)
            self.warnings = self._context.__enter__()
            warnings.simplefilter("always", FinTSParserWarning)
            return self

        def __exit__(self, *args):
            return self._context.__exit__(*args)

        @property
        def parser_warnings(self) -> list[warnings.WarningMessage]:
            return [w for w in self.warnings if issubclass(w.category, FinTSParserWarning)]

        @property
        def unknown_segments(self) -> list[str]:
            return [
                str(w.message) for w in self.parser_warnings
                if "Unknown segment type" in str(w.message)
            ]

        @property
        def parse_errors(self) -> list[str]:
            return [
                str(w.message) for w in self.parser_warnings
                if "Error parsing" in str(w.message)
            ]

        def report(self) -> str:
            if not self.parser_warnings:
                return "No parser warnings"
            lines = [f"Parser Warnings ({len(self.parser_warnings)}):"]
            for w in self.parser_warnings:
                lines.append(f"  - {w.message}")
            return "\n".join(lines)

        def assert_no_warnings(self, msg: str = ""):
            if self.parser_warnings:
                pytest.fail(f"{msg}\n{self.report()}")

    return WarningCollector()


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
