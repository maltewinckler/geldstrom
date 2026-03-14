"""Read raw FinTS institute rows from the upstream CSV export."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

from gateway.domain.institution_catalog import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
)


class InstituteCsvReader:
    """Parse raw institute CSV rows into domain objects without deduplicating them."""

    def read(self, path: Path) -> list[FinTSInstitute]:
        with path.open("r", encoding="latin-1", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            return [self._build_institute(row) for row in reader]

    def _build_institute(self, row: dict[str, str]) -> FinTSInstitute:
        normalized_payload = {
            key.strip(): value.strip()
            for key, value in row.items()
            if key is not None and value is not None
        }
        checksum_source = json.dumps(
            normalized_payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        updated_at = normalized_payload.get(
            "Datum letzte Änderung"
        ) or normalized_payload.get("Datum letzte �nderung")
        return FinTSInstitute(
            blz=BankLeitzahl(normalized_payload["BLZ"]),
            bic=Bic(normalized_payload["BIC"])
            if normalized_payload.get("BIC")
            else None,
            name=normalized_payload["Institut"],
            city=normalized_payload.get("Ort") or None,
            organization=normalized_payload.get("Organisation") or None,
            pin_tan_url=(
                InstituteEndpoint(normalized_payload["PIN/TAN-Zugang URL"])
                if normalized_payload.get("PIN/TAN-Zugang URL")
                else None
            ),
            fints_version=normalized_payload.get("Version")
            or normalized_payload.get("HBCI-Version")
            or None,
            last_source_update=(
                datetime.strptime(updated_at, "%d.%m.%Y").date() if updated_at else None
            ),
            source_row_checksum=hashlib.sha256(checksum_source).hexdigest(),
            source_payload=normalized_payload,
        )
