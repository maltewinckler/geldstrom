"""Tests for raw institute CSV parsing."""

from pathlib import Path

from gateway.infrastructure.persistence.csv import InstituteCsvReader


def test_csv_reader_parses_fixture_and_preserves_duplicates() -> None:
    reader = InstituteCsvReader()

    institutes = reader.read(
        Path(
            "/home/malte/Documents/projects/code/geldstrom/tests/apps/gateway/fixtures/institutes/sample_fints_institute.csv"
        )
    )

    assert len(institutes) == 3
    assert institutes[0].blz.value == "10010010"
    assert institutes[0].pin_tan_url is not None
    assert institutes[1].blz.value == "10010010"
    assert institutes[1].source_row_checksum != institutes[0].source_row_checksum
