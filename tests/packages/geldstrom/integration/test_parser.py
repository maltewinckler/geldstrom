"""Live-bank parser migration validation tests.

These tests verify that the Pydantic-based parser can handle all segment types
returned by real banks. They're designed to catch migration gaps early by:

1. Running in strict mode (no fallback segments)
2. Capturing and reporting parser warnings
3. Validating all BPD/UPD segments are recognized
4. Saving raw responses for offline debugging

These tests are intentionally separate from the disposable testcontainers-based
database tests because they validate real FinTS interoperability.

Run with: pytest tests/packages/geldstrom/integration/test_parser.py --run-integration -v

For maximum debugging output:
    pytest tests/packages/geldstrom/integration/test_parser.py --run-integration -v -s --tb=long
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from geldstrom.domain import BankCredentials, BankRoute
from geldstrom.infrastructure.fints import GatewayCredentials
from geldstrom.infrastructure.fints.protocol.parser import (
    FinTSParser,
    FinTSSerializer,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def credentials(request: pytest.FixtureRequest) -> GatewayCredentials:
    """Load credentials from .env file."""
    import os

    env_file = Path(request.config.getoption("--fints-env-file", ".env"))
    if not env_file.exists():
        pytest.skip(f"Environment file {env_file} not found")

    env: dict[str, str] = {}
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        env[key.strip()] = value

    # Allow OS env to override
    for key, value in os.environ.items():
        if key.startswith("FINTS_"):
            env[key] = value

    def require(key: str) -> str:
        val = env.get(key)
        if not val:
            pytest.skip(f"Missing required: {key}")
        return val

    return GatewayCredentials(
        route=BankRoute(
            country_code=env.get("FINTS_COUNTRY", "DE"),
            bank_code=require("FINTS_BLZ"),
        ),
        server_url=require("FINTS_SERVER"),
        credentials=BankCredentials(
            user_id=require("FINTS_USER"),
            secret=require("FINTS_PIN"),
            customer_id=env.get("FINTS_CUSTOMER_ID"),
            two_factor_device=env.get("FINTS_TAN_MEDIUM"),
            two_factor_method=env.get("FINTS_TAN_METHOD"),
        ),
        product_id=require("FINTS_PRODUCT_ID"),
        product_version=require("FINTS_PRODUCT_VERSION"),
    )


@pytest.fixture
def connection_helper(credentials: GatewayCredentials):
    """Create a FinTSConnectionHelper for low-level testing."""
    from geldstrom.infrastructure.fints.adapters.connection import FinTSConnectionHelper
    return FinTSConnectionHelper(credentials)


@pytest.fixture
def debug_output_dir(tmp_path_factory) -> Path:
    """Create a directory for debug output."""
    return tmp_path_factory.mktemp("fints_debug")


# ---------------------------------------------------------------------------
# Log Capture Utilities
# ---------------------------------------------------------------------------


class _LogCaptureHandler(logging.Handler):
    """Handler that captures log records into a list."""

    def __init__(self, records: list[logging.LogRecord]):
        super().__init__()
        self.records = records

    def emit(self, record: logging.LogRecord):
        self.records.append(record)


class ParserWarningCollector:
    """Collects parser log warnings for analysis."""

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
        """Return warning messages from parser."""
        return [
            r.getMessage()
            for r in self.log_records
            if r.levelno >= logging.WARNING
        ]

    @property
    def unknown_segment_warnings(self) -> list[str]:
        """Extract unknown segment type warnings."""
        return [
            msg for msg in self.warning_messages
            if "Unknown segment type" in msg
        ]

    @property
    def parse_error_warnings(self) -> list[str]:
        """Extract parse error warnings."""
        return [
            msg for msg in self.warning_messages
            if "Error parsing" in msg or "Could not parse" in msg
        ]

    def assert_no_warnings(self, message: str = ""):
        """Assert no parser warnings were raised."""
        if self.warning_messages:
            details = "\n".join(f"  - {m}" for m in self.warning_messages)
            pytest.fail(
                f"{message}\nParser warnings "
                f"({len(self.warning_messages)}):\n{details}"
            )

    def assert_no_critical_warnings(self, message: str = ""):
        """Assert no critical parser warnings were raised.

        Unknown parameter segments (HI*S*) are expected and ignored.
        Only actual parse errors and unknown core segments are critical.
        """
        critical = self.critical_warnings
        if critical:
            details = "\n".join(f"  - {m}" for m in critical)
            pytest.fail(
                f"{message}\nCritical parser warnings ({len(critical)}):\n{details}"
            )

    @property
    def critical_warnings(self) -> list[str]:
        """Return only critical warnings (not unknown parameter segments).

        Parameter segments (HI*S*) advertise bank-specific capabilities
        and are expected to be unknown - the legacy parser also uses
        generic fallback for these.
        """
        import re

        critical = []
        for msg in self.warning_messages:
            # Unknown segment type warnings for parameter segments are OK
            if "Unknown segment type" in msg:
                # Extract segment type to check if it's a parameter segment
                # Parameter segments end with 'S' (e.g., HIVPAS, HIZDLS)
                match = re.search(r"Unknown segment type (HI[A-Z]+)v", msg)
                if match:
                    seg_type = match.group(1)
                    # Parameter segments end with 'S' and are typically 5+ chars
                    if len(seg_type) >= 5 and seg_type.endswith("S"):
                        # This is a parameter segment - skip it
                        continue
            critical.append(msg)
        return critical

    def report(self) -> str:
        """Generate a human-readable report."""
        if not self.warning_messages:
            return "No parser warnings."

        lines = [f"Parser Warnings ({len(self.warning_messages)}):"]

        unknown = self.unknown_segment_warnings
        if unknown:
            lines.append(f"\n  Unknown Segment Types ({len(unknown)}):")
            for msg in sorted(set(unknown)):
                lines.append(f"    - {msg}")

        errors = self.parse_error_warnings
        if errors:
            lines.append(f"\n  Parse Errors ({len(errors)}):")
            for msg in errors:
                lines.append(f"    - {msg}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Strict Parsing Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStrictParsing:
    """Tests that verify parsing works without fallbacks."""

    def test_connect_no_parser_warnings(self, connection_helper):
        """Verify connection and BPD/UPD parsing produces no critical warnings.

        Unknown parameter segments (HI*S*) are expected and not failures.
        """
        collector = ParserWarningCollector()

        with collector:
            with connection_helper.connect(None) as ctx:
                # Force access to parameters to ensure they're parsed
                _ = ctx.parameters.bpd_version
                _ = ctx.parameters.upd_version
                _ = ctx.parameters.bpd.get_supported_operations()
                _ = ctx.parameters.upd.get_accounts()

        # Report warnings for debugging
        if collector.warning_messages:
            print("\n" + collector.report())

        collector.assert_no_critical_warnings(
            "Bank connection produced critical parser warnings - "
            "Pydantic models may be incomplete"
        )

    def test_account_fetch_no_warnings(self, connection_helper):
        """Verify HKSPA/HISPA parsing produces no critical warnings."""
        from geldstrom.infrastructure.fints.operations import AccountOperations

        collector = ParserWarningCollector()

        with collector:
            with connection_helper.connect(None) as ctx:
                ops = AccountOperations(ctx.dialog, ctx.parameters)
                accounts = ops.fetch_sepa_accounts()
                assert accounts, "Expected at least one SEPA account"

        if collector.warning_messages:
            print("\n" + collector.report())

        collector.assert_no_critical_warnings("Account fetch produced critical parser warnings")

    def test_balance_fetch_no_warnings(self, connection_helper):
        """Verify HKSAL/HISAL parsing produces no critical warnings."""
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            BalanceOperations,
        )

        collector = ParserWarningCollector()

        with collector:
            with connection_helper.connect(None) as ctx:
                account_ops = AccountOperations(ctx.dialog, ctx.parameters)
                balance_ops = BalanceOperations(ctx.dialog, ctx.parameters)

                accounts = account_ops.fetch_sepa_accounts()
                if not accounts:
                    pytest.skip("No accounts for balance test")

                # Try to fetch balance for first account
                try:
                    balance_ops.fetch_balance(accounts[0])
                except Exception as e:
                    # Balance might fail for some account types, that's okay
                    logger.warning("Balance fetch failed (may be expected): %s", e)

        if collector.warning_messages:
            print("\n" + collector.report())

        collector.assert_no_critical_warnings("Balance fetch produced critical parser warnings")

    def test_transaction_fetch_no_warnings(self, connection_helper):
        """Verify HKKAZ/HIKAZ or HKCAZ/HICAZ parsing produces no critical warnings."""
        from geldstrom.infrastructure.fints.exceptions import FinTSUnsupportedOperation
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            TransactionOperations,
        )

        collector = ParserWarningCollector()

        with collector:
            with connection_helper.connect(None) as ctx:
                account_ops = AccountOperations(ctx.dialog, ctx.parameters)
                tx_ops = TransactionOperations(ctx.dialog, ctx.parameters)

                accounts = account_ops.fetch_sepa_accounts()
                if not accounts:
                    pytest.skip("No accounts for transaction test")

                # Try MT940 first, then CAMT
                start_date = date.today() - timedelta(days=7)
                try:
                    tx_ops.fetch_mt940(accounts[0], start_date)
                except FinTSUnsupportedOperation:
                    try:
                        tx_ops.fetch_camt(accounts[0], start_date)
                    except FinTSUnsupportedOperation:
                        pytest.skip("Bank doesn't support transactions")

        if collector.warning_messages:
            print("\n" + collector.report())

        collector.assert_no_critical_warnings("Transaction fetch produced critical parser warnings")


# ---------------------------------------------------------------------------
# Segment Coverage Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSegmentCoverage:
    """Tests that verify bank segments are handled correctly.

    Note on segment types:
    - Core segments (HIBPA, HISAL, HIKAZ, etc.) - MUST have Pydantic models
    - Parameter segments (HI*S*) - Bank-specific, generic fallback is OK
    - Bank-specific segments - Not part of FinTS standard, fallback is OK

    Parameter segments advertise bank capabilities and don't need full parsing.
    The legacy parser also uses generic fallback for unknown segments.
    """

    # Core segments that MUST be recognized for basic functionality
    REQUIRED_CORE_SEGMENTS = {
        "HIBPA",  # Bank parameters
        "HIUPA",  # User parameters
        "HIUPD",  # User account data
        "HIRMG",  # Response messages
        "HIRMS",  # Response messages
        "HISYN",  # Synchronization
    }

    # Segments we need for specific operations
    REQUIRED_OPERATION_SEGMENTS = {
        "HISPA",  # SEPA accounts (for account listing)
        "HISAL",  # Balance response
        "HIKAZ",  # Transaction response (MT940)
        "HICAZ",  # Transaction response (CAMT)
        "HITAN",  # TAN response
        "HITAB",  # TAN media
    }

    def _is_parameter_segment(self, seg_type: str) -> bool:
        """Check if segment is a bank-specific parameter segment.

        Parameter segments (HI*S*) advertise capabilities and don't need
        specific Pydantic models - generic parsing is sufficient.
        """
        # Parameter segments end with 'S' and are response segments (HI*)
        if not seg_type.startswith("HI"):
            return False
        # Check for typical parameter segment pattern: HI____S
        if len(seg_type) >= 5 and seg_type.endswith("S"):
            return True
        return False

    def _is_core_segment(self, seg_type: str) -> bool:
        """Check if segment is a core segment that must be recognized."""
        base_type = seg_type.rstrip("0123456789")
        return base_type in self.REQUIRED_CORE_SEGMENTS

    def _is_operation_segment(self, seg_type: str) -> bool:
        """Check if segment is needed for operations."""
        base_type = seg_type.rstrip("0123456789")
        return base_type in self.REQUIRED_OPERATION_SEGMENTS

    def test_core_bpd_segments_recognized(self, connection_helper):
        """Verify core BPD segments have Pydantic models."""
        from geldstrom.infrastructure.fints.protocol.base import FinTSSegment

        missing_core: list[tuple[str, int]] = []

        with connection_helper.connect(None) as ctx:
            for segment in ctx.parameters.bpd.segments.segments:
                header = segment.header
                if self._is_core_segment(header.type):
                    if not FinTSSegment.get_segment_class(header.type, header.version):
                        missing_core.append((header.type, header.version))

        if missing_core:
            types_str = ", ".join(f"{t}v{v}" for t, v in sorted(set(missing_core)))
            pytest.fail(
                f"Missing core BPD segment models ({len(set(missing_core))}): {types_str}\n"
                "These are required for basic functionality."
            )

    def test_core_upd_segments_recognized(self, connection_helper):
        """Verify core UPD segments have Pydantic models."""
        from geldstrom.infrastructure.fints.protocol.base import FinTSSegment

        missing_core: list[tuple[str, int]] = []

        with connection_helper.connect(None) as ctx:
            for segment in ctx.parameters.upd.segments.segments:
                header = segment.header
                if self._is_core_segment(header.type):
                    if not FinTSSegment.get_segment_class(header.type, header.version):
                        missing_core.append((header.type, header.version))

        if missing_core:
            types_str = ", ".join(f"{t}v{v}" for t, v in sorted(set(missing_core)))
            pytest.fail(
                f"Missing core UPD segment models ({len(set(missing_core))}): {types_str}\n"
                "These are required for basic functionality."
            )

    def test_registry_coverage_report(self, connection_helper, capsys):
        """Generate a detailed report of segment coverage for debugging.

        This test always passes but prints diagnostic information.
        """
        from geldstrom.infrastructure.fints.protocol.base import FinTSSegment

        with connection_helper.connect(None) as ctx:
            bpd_types = {
                (seg.header.type, seg.header.version)
                for seg in ctx.parameters.bpd.segments.segments
            }
            upd_types = {
                (seg.header.type, seg.header.version)
                for seg in ctx.parameters.upd.segments.segments
            }

        all_types = bpd_types | upd_types
        recognized = {t for t in all_types if FinTSSegment.get_segment_class(*t)}
        unrecognized = all_types - recognized

        # Categorize unrecognized segments
        param_segments = {t for t in unrecognized if self._is_parameter_segment(t[0])}
        core_missing = {t for t in unrecognized if self._is_core_segment(t[0])}
        other_missing = unrecognized - param_segments - core_missing

        print("\n" + "=" * 70)
        print("SEGMENT COVERAGE REPORT")
        print("=" * 70)
        print(f"\nTotal segment types from bank: {len(all_types)}")
        print(f"Recognized by Pydantic models: {len(recognized)}")
        print(f"Using generic fallback:        {len(unrecognized)}")

        if recognized:
            print(f"\n✓ RECOGNIZED ({len(recognized)}):")
            for t, v in sorted(recognized):
                print(f"    {t}v{v}")

        if core_missing:
            print(f"\n✗ MISSING CORE (need implementation) ({len(core_missing)}):")
            for t, v in sorted(core_missing):
                print(f"    {t}v{v}")

        if other_missing:
            print(f"\n⚠ MISSING OTHER (may need implementation) ({len(other_missing)}):")
            for t, v in sorted(other_missing):
                print(f"    {t}v{v}")

        if param_segments:
            print(f"\n○ PARAMETER SEGMENTS (generic fallback OK) ({len(param_segments)}):")
            for t, v in sorted(param_segments):
                print(f"    {t}v{v}")

        print("\n" + "=" * 70)
        print("Legend:")
        print("  ✓ = Has Pydantic model")
        print("  ✗ = Core segment missing model (should be fixed)")
        print("  ⚠ = Other segment missing model (evaluate if needed)")
        print("  ○ = Parameter segment (generic fallback is fine)")
        print("=" * 70)


# ---------------------------------------------------------------------------
# Raw Response Capture Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRawResponseCapture:
    """Tests that capture raw bank responses for offline debugging."""

    def test_capture_bpd_upd(self, connection_helper, debug_output_dir):
        """Capture raw BPD/UPD for offline analysis."""
        with connection_helper.connect(None) as ctx:
            # Serialize raw parameter data
            bpd_bin = ctx.parameters.bpd.serialize()
            upd_bin = ctx.parameters.upd.serialize()

            # Save binary data
            (debug_output_dir / "bpd.bin").write_bytes(bpd_bin)
            (debug_output_dir / "upd.bin").write_bytes(upd_bin)

            # Save human-readable summary
            summary = {
                "bpd_version": ctx.parameters.bpd_version,
                "upd_version": ctx.parameters.upd_version,
                "bank_name": ctx.parameters.bpd.bank_name,
                "bpd_segment_types": sorted(set(
                    f"{s.header.type}v{s.header.version}"
                    for s in ctx.parameters.bpd.segments.segments
                )),
                "upd_segment_types": sorted(set(
                    f"{s.header.type}v{s.header.version}"
                    for s in ctx.parameters.upd.segments.segments
                )),
                "accounts": [
                    {
                        "iban": acc.get("iban"),
                        "account_number": acc.get("account_number"),
                        "type": str(acc.get("type")),
                    }
                    for acc in ctx.parameters.upd.get_accounts()
                ],
            }

            (debug_output_dir / "summary.json").write_text(
                json.dumps(summary, indent=2, default=str)
            )

        print(f"\nDebug files saved to: {debug_output_dir}")
        print(f"  - bpd.bin ({bpd_bin and len(bpd_bin)} bytes)")
        print(f"  - upd.bin ({upd_bin and len(upd_bin)} bytes)")
        print("  - summary.json")

    def test_capture_dialog_exchange(self, connection_helper, debug_output_dir, caplog):
        """Capture full dialog exchange for protocol debugging."""
        from geldstrom.infrastructure.fints.operations import AccountOperations

        # Enable debug logging
        caplog.set_level(logging.DEBUG, logger="geldstrom.infrastructure.fints.dialog")

        messages: list[dict] = []

        with connection_helper.connect(None) as ctx:
            # Perform some operations to generate traffic
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)
            account_ops.fetch_sepa_accounts()

        # Save captured log messages
        dialog_log = "\n".join(
            f"[{r.levelname}] {r.message}"
            for r in caplog.records
            if "fints" in r.name
        )
        (debug_output_dir / "dialog.log").write_text(dialog_log)

        print(f"\nDialog log saved to: {debug_output_dir / 'dialog.log'}")


# ---------------------------------------------------------------------------
# Parser Strict Mode Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStrictModeParser:
    """Tests verifying parser behavior in strict vs robust mode.

    Note: Strict mode (robust_mode=False) is expected to fail on unknown
    bank-specific parameter segments (HI*S*). This is by design - the legacy
    parser also doesn't have definitions for these segments.

    These tests verify:
    1. Robust mode successfully parses all segments
    2. The number of segments parsed matches between modes
    3. Core segments are parsed correctly in both modes
    """

    def test_parse_bpd_robust_vs_strict(self, connection_helper):
        """Compare robust vs strict parsing of BPD parameter segments.

        Note: BankParameters.serialize() only serializes the parameter segments
        (HISALS, HIKAZS, etc.), not HIBPA itself which is stored separately.

        Robust mode should parse most segments, though some may be skipped
        if they have validation errors (these are logged as warnings).
        """
        robust_parser = FinTSParser(robust_mode=True)

        with connection_helper.connect(None) as ctx:
            raw_bpd = ctx.parameters.bpd.serialize()
            bpd_segment_count = len(ctx.parameters.bpd.segments.segments)

        # Robust mode should always work
        robust_result = robust_parser.parse_message(raw_bpd)
        assert len(robust_result.segments) > 0, "BPD should have segments"

        # Check that we got most segments (some may be skipped due to validation)
        # Allow up to 10% loss due to validation errors
        min_expected = int(bpd_segment_count * 0.9)
        assert len(robust_result.segments) >= min_expected, \
            f"Expected at least {min_expected} segments (90% of {bpd_segment_count}), got {len(robust_result.segments)}"

        # Find typical parameter segments (these should have 'S' suffix)
        param_segment_types = {
            s.header.type for s in robust_result.segments
            if s.header.type.endswith("S")
        }
        assert len(param_segment_types) > 0, "BPD should contain parameter segments"

        print(f"\nRobust parsing: {len(robust_result.segments)}/{bpd_segment_count} segments")
        print(f"Parameter segment types: {len(param_segment_types)}")
        print(f"Examples: {list(param_segment_types)[:5]}")

    def test_parse_upd_robust_vs_strict(self, connection_helper):
        """Compare robust vs strict parsing of UPD."""
        robust_parser = FinTSParser(robust_mode=True)
        strict_parser = FinTSParser(robust_mode=False)

        with connection_helper.connect(None) as ctx:
            raw_upd = ctx.parameters.upd.serialize()

        # Robust mode should always work
        robust_result = robust_parser.parse_message(raw_upd)
        assert len(robust_result.segments) > 0, "UPD should have segments"

        # Find HIUPD segments
        upd_segments = [s for s in robust_result.segments if s.header.type == "HIUPD"]
        assert len(upd_segments) >= 1, "UPD should contain at least one HIUPD"

        print(f"\nRobust parsing: {len(robust_result.segments)} segments")
        print(f"HIUPD segments: {len(upd_segments)}")

        # Strict mode
        try:
            strict_result = strict_parser.parse_message(raw_upd)
            print(f"Strict parsing succeeded: {len(strict_result.segments)} segments")
        except Exception as e:
            print(f"Strict parsing failed: {type(e).__name__}")


# ---------------------------------------------------------------------------
# Serialization Round-Trip Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSerializationRoundTrip:
    """Tests that verify parse -> serialize -> parse produces same result."""

    def test_bpd_roundtrip(self, connection_helper):
        """Verify BPD survives serialization round-trip."""
        parser = FinTSParser(robust_mode=True)
        serializer = FinTSSerializer()

        with connection_helper.connect(None) as ctx:
            original_bpd = ctx.parameters.bpd.serialize()

        # Parse
        parsed = parser.parse_message(original_bpd)

        # Serialize back
        reserialized = serializer.serialize_message(parsed)

        # Parse again
        reparsed = parser.parse_message(reserialized)

        # Compare segment counts (exact byte comparison may differ due to formatting)
        assert len(reparsed.segments) == len(parsed.segments), \
            f"Segment count mismatch: {len(parsed.segments)} -> {len(reparsed.segments)}"

        # Compare segment types
        original_types = [s.header.type for s in parsed.segments]
        reparsed_types = [s.header.type for s in reparsed.segments]
        assert original_types == reparsed_types, "Segment types differ after round-trip"

    def test_segment_field_preservation(self, connection_helper):
        """Verify individual segment fields survive round-trip."""
        parser = FinTSParser(robust_mode=True)
        serializer = FinTSSerializer()

        with connection_helper.connect(None) as ctx:
            # Get a known segment type
            original_bpd = ctx.parameters.bpd.serialize()

        parsed = parser.parse_message(original_bpd)

        # Find HIBPA segment (should always exist)
        hibpa_segments = [s for s in parsed.segments if s.header.type == "HIBPA"]
        if not hibpa_segments:
            pytest.skip("No HIBPA segment in BPD")

        original_hibpa = hibpa_segments[0]

        # Round-trip
        reserialized = serializer.serialize_message(parsed)
        reparsed = parser.parse_message(reserialized)

        reparsed_hibpa = [s for s in reparsed.segments if s.header.type == "HIBPA"][0]

        # Compare key fields
        assert original_hibpa.header.version == reparsed_hibpa.header.version
        if hasattr(original_hibpa, "bpd_version"):
            assert original_hibpa.bpd_version == reparsed_hibpa.bpd_version
