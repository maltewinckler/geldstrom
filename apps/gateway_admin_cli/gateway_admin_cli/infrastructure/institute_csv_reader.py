"""Read raw FinTS institute rows from the upstream CSV export."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from gateway_admin_cli.domain.errors import DomainError
from gateway_admin_cli.domain.institutes import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
    SkippedRow,
)

_BLZ_RE = re.compile(r"^\d{8}$")


class InstituteCsvReader:
    """Parse raw institute CSV rows into domain objects.

    Returns a tuple of ``(valid_institutes, skipped_rows)``.
    Rows with an empty or non-8-digit BLZ are silently dropped (blank rows).
    Rows with a valid BLZ that fail for any other reason are reported as skipped.
    """

    def read(self, path: Path) -> tuple[list[FinTSInstitute], list[SkippedRow]]:
        institutes: list[FinTSInstitute] = []
        skipped: list[SkippedRow] = []

        with path.open("r", encoding="latin-1", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            # Detect the date column regardless of how the encoding was mangled
            # ("Datum letzte Änderung" may decode differently across Excel exports)
            date_key = next(
                (k.strip() for k in (reader.fieldnames or []) if k and "nderung" in k),
                None,
            )
            for row in reader:
                normalized = {
                    k.strip(): v.strip()
                    for k, v in row.items()
                    if k is not None and v is not None
                }
                raw_blz = normalized.get("BLZ", "")
                if not _BLZ_RE.match(raw_blz):
                    # Blank/padding rows — no usable identifier, skip silently
                    continue
                try:
                    institutes.append(self._build_institute(normalized, date_key))
                except Exception as exc:
                    skipped.append(
                        SkippedRow(
                            blz=raw_blz,
                            name=normalized.get("Institut", ""),
                            reason=str(exc),
                        )
                    )

        return institutes, skipped

    def _parse_bic(self, raw: str | None) -> Bic | None:
        """Return a Bic, or None for absent/invalid values (e.g. Excel '#NV', '0')."""
        if not raw:
            return None
        try:
            return Bic(raw)
        except DomainError:
            return None

    def _build_institute(
        self, normalized: dict[str, str], date_key: str | None
    ) -> FinTSInstitute:
        checksum_source = json.dumps(
            normalized,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        raw_date = normalized.get(date_key) if date_key else None
        return FinTSInstitute(
            blz=BankLeitzahl(normalized["BLZ"]),
            bic=self._parse_bic(normalized.get("BIC")),
            name=normalized["Institut"],
            city=normalized.get("Ort") or None,
            organization=normalized.get("Organisation") or None,
            pin_tan_url=(
                InstituteEndpoint(normalized["PIN/TAN-Zugang URL"])
                if normalized.get("PIN/TAN-Zugang URL")
                else None
            ),
            fints_version=(
                normalized.get("Version") or normalized.get("HBCI-Version") or None
            ),
            last_source_update=(
                datetime.strptime(raw_date, "%d.%m.%Y").date() if raw_date else None
            ),
            source_row_checksum=hashlib.sha256(checksum_source).hexdigest(),
            source_payload=normalized,
        )
