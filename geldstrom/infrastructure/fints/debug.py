"""Debugging utilities for FinTS protocol development.

This module provides tools for debugging parser issues, capturing raw responses,
and analyzing bank communication during development and migration.

Usage:
    from geldstrom.infrastructure.fints.debug import (
        ParserDebugger,
        capture_bank_response,
        analyze_segments,
    )

    # Capture and analyze a bank connection
    debugger = ParserDebugger()
    with debugger.capture():
        client.connect()

    print(debugger.report())
"""

from __future__ import annotations

import json
import logging
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from geldstrom.infrastructure.fints.protocol.base import FinTSSegment
from geldstrom.infrastructure.fints.protocol.parser import FinTSParser

logger = logging.getLogger(__name__)


@dataclass
class SegmentAnalysis:
    """Analysis result for a single segment type."""

    segment_type: str
    version: int
    count: int = 0
    recognized: bool = False
    parse_errors: list[str] = field(default_factory=list)


@dataclass
class ParserReport:
    """Report of parser analysis results."""

    total_segments: int = 0
    recognized_count: int = 0
    unrecognized_count: int = 0
    error_count: int = 0
    segments: dict[tuple[str, int], SegmentAnalysis] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def add_segment(self, seg_type: str, version: int, recognized: bool):
        """Record a parsed segment."""
        key = (seg_type, version)
        if key not in self.segments:
            self.segments[key] = SegmentAnalysis(
                segment_type=seg_type,
                version=version,
                recognized=recognized,
            )
        self.segments[key].count += 1
        self.total_segments += 1
        if recognized:
            self.recognized_count += 1
        else:
            self.unrecognized_count += 1

    def add_warning(self, message: str):
        """Record a parser warning."""
        self.warnings.append(message)

    def add_error(self, seg_type: str, version: int, error: str):
        """Record a parse error for a segment."""
        key = (seg_type, version)
        if key in self.segments:
            self.segments[key].parse_errors.append(error)
        self.error_count += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_segments": self.total_segments,
            "recognized_count": self.recognized_count,
            "unrecognized_count": self.unrecognized_count,
            "error_count": self.error_count,
            "segments": {
                f"{k[0]}v{k[1]}": {
                    "count": v.count,
                    "recognized": v.recognized,
                    "errors": v.parse_errors,
                }
                for k, v in sorted(self.segments.items())
            },
            "warnings": self.warnings,
        }

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            "=" * 60,
            "PARSER ANALYSIS REPORT",
            "=" * 60,
            f"Total segments:    {self.total_segments}",
            f"Recognized:        {self.recognized_count}",
            f"Unrecognized:      {self.unrecognized_count}",
            f"Parse errors:      {self.error_count}",
            "",
        ]

        if self.unrecognized_count > 0:
            lines.append("UNRECOGNIZED SEGMENT TYPES:")
            for key, analysis in sorted(self.segments.items()):
                if not analysis.recognized:
                    lines.append(f"  - {key[0]}v{key[1]} (count: {analysis.count})")
            lines.append("")

        if self.error_count > 0:
            lines.append("PARSE ERRORS:")
            for key, analysis in sorted(self.segments.items()):
                for error in analysis.parse_errors:
                    lines.append(f"  - {key[0]}v{key[1]}: {error}")
            lines.append("")

        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:10]:  # Limit to first 10
                lines.append(f"  - {warning}")
            if len(self.warnings) > 10:
                lines.append(f"  ... and {len(self.warnings) - 10} more")

        lines.append("=" * 60)
        return "\n".join(lines)


class ParserDebugger:
    """Debugger for analyzing FinTS parser behavior.

    This class captures parser warnings and analyzes segment recognition
    during bank communication.

    Example:
        debugger = ParserDebugger()

        with debugger.capture():
            # Code that triggers parsing
            client.connect()

        # Print analysis
        print(debugger.report.summary())

        # Or save to file
        debugger.save_report("debug_report.json")
    """

    def __init__(self):
        self.report = ParserReport()
        self._warning_context = None
        self._captured_warnings: list[warnings.WarningMessage] = []

    def capture(self):
        """Context manager to capture parser warnings.

        Usage:
            with debugger.capture():
                # ... parsing happens here ...
        """
        return _CaptureContext(self)

    def analyze_bytes(self, data: bytes, source: str = "unknown") -> ParserReport:
        """Analyze raw FinTS message bytes.

        Args:
            data: Raw FinTS wire format bytes
            source: Description of where the data came from

        Returns:
            ParserReport with analysis results
        """
        report = ParserReport()

        # Capture log records during parsing
        log_records: list[logging.LogRecord] = []
        handler = _LogCaptureHandler(log_records)
        parser_logger = logging.getLogger(
            "geldstrom.infrastructure.fints.protocol.parser"
        )
        parser_logger.addHandler(handler)
        old_level = parser_logger.level
        parser_logger.setLevel(logging.WARNING)

        try:
            parser = FinTSParser(robust_mode=True)

            try:
                result = parser.parse_message(data)

                # Analyze each segment
                for segment in result.segments:
                    header = segment.header
                    is_recognized = (
                        FinTSSegment.get_segment_class(header.type, header.version)
                        is not None
                    )
                    report.add_segment(header.type, header.version, is_recognized)

            except Exception as e:
                report.add_warning(f"Fatal parse error: {e}")

            # Process captured log records
            for record in log_records:
                if record.levelno >= logging.WARNING:
                    report.add_warning(record.getMessage())

        finally:
            parser_logger.removeHandler(handler)
            parser_logger.setLevel(old_level)

        return report

    def save_report(self, path: str | Path):
        """Save report to JSON file."""
        path = Path(path)
        data = {
            "timestamp": datetime.now().isoformat(),
            "report": self.report.to_dict(),
        }
        path.write_text(json.dumps(data, indent=2))
        logger.info("Saved debug report to %s", path)


class _LogCaptureHandler(logging.Handler):
    """Handler that captures log records into a list."""

    def __init__(self, records: list[logging.LogRecord]):
        super().__init__()
        self.records = records

    def emit(self, record: logging.LogRecord):
        self.records.append(record)


class _CaptureContext:
    """Context manager for capturing parser log messages."""

    def __init__(self, debugger: ParserDebugger):
        self._debugger = debugger
        self._records: list[logging.LogRecord] = []
        self._handler: _LogCaptureHandler | None = None
        self._logger: logging.Logger | None = None
        self._old_level: int = logging.NOTSET

    def __enter__(self):
        self._records = []
        self._handler = _LogCaptureHandler(self._records)
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

        # Process captured log records into report
        for record in self._records:
            if record.levelno >= logging.WARNING:
                self._debugger.report.add_warning(record.getMessage())

        return False


def analyze_segments(data: bytes) -> ParserReport:
    """Analyze raw FinTS data for segment recognition.

    This is a convenience function for quick analysis.

    Args:
        data: Raw FinTS wire format bytes

    Returns:
        ParserReport with analysis results
    """
    debugger = ParserDebugger()
    return debugger.analyze_bytes(data)


def capture_bank_response(
    output_dir: str | Path,
    credentials,
    operations: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Capture raw bank responses for offline debugging.

    This function connects to a bank and saves all responses
    for later analysis.

    Args:
        output_dir: Directory to save captured data
        credentials: GatewayCredentials for bank connection
        operations: Optional list of operations to perform
                   ("accounts", "balance", "transactions")

    Returns:
        Dict with capture summary
    """
    from geldstrom.infrastructure.fints.adapters.connection import FinTSConnectionHelper
    from geldstrom.infrastructure.fints.operations import AccountOperations

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    helper = FinTSConnectionHelper(credentials)
    summary: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "files": [],
    }

    debugger = ParserDebugger()

    with debugger.capture(), helper.connect(None) as ctx:
        # Save BPD
        bpd_data = ctx.parameters.bpd.serialize()
        (output_dir / "bpd.bin").write_bytes(bpd_data)
        summary["files"].append("bpd.bin")
        summary["bpd_version"] = ctx.parameters.bpd_version

        # Save UPD
        upd_data = ctx.parameters.upd.serialize()
        (output_dir / "upd.bin").write_bytes(upd_data)
        summary["files"].append("upd.bin")
        summary["upd_version"] = ctx.parameters.upd_version

        # Analyze segments
        bpd_report = debugger.analyze_bytes(bpd_data, "BPD")
        upd_report = debugger.analyze_bytes(upd_data, "UPD")

        summary["bpd_segments"] = bpd_report.to_dict()
        summary["upd_segments"] = upd_report.to_dict()

        # Perform requested operations
        if operations:
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)

            if "accounts" in operations:
                accounts = account_ops.fetch_sepa_accounts()
                summary["accounts"] = [
                    {"iban": a.iban, "number": a.accountnumber} for a in accounts
                ]

    # Save summary
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    summary["files"].append("summary.json")

    # Save parser report
    debugger.save_report(output_dir / "parser_report.json")
    summary["files"].append("parser_report.json")

    logger.info("Captured bank response to %s", output_dir)
    return summary


__all__ = [
    "ParserDebugger",
    "ParserReport",
    "SegmentAnalysis",
    "analyze_segments",
    "capture_bank_response",
]
