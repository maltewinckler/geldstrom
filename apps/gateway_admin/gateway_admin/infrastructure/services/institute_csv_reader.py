"""FinTS institute CSV reader - implements InstituteCsvReaderPort."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Self

from gateway_admin.domain.entities.institutes import FinTSInstitute
from gateway_admin.domain.errors import DomainError
from gateway_admin.domain.services.institute_csv import (
    InstituteCsvReaderPort,
)
from gateway_admin.domain.value_objects.institutes import (
    BankLeitzahl,
    Bic,
    InstituteEndpoint,
    SkippedRow,
)

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory

_BLZ_RE = re.compile(r"^\d{8}$")


class InstituteCsvReader(InstituteCsvReaderPort):
    """Parse raw institute CSV rows into ``(valid_institutes, skipped_rows)``."""

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:  # noqa: ARG003
        return cls()

    def read(self, path: Path) -> tuple[list[FinTSInstitute], list[SkippedRow]]:
        institutes: list[FinTSInstitute] = []
        skipped: list[SkippedRow] = []

        with path.open("r", encoding="latin-1", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
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
