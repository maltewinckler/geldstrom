"""Institute CSV reader port."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from gateway.domain.institution_catalog import FinTSInstitute


class InstituteCsvReaderPort(Protocol):
    """Reads raw institute rows from an operator-supplied CSV path."""

    def read(self, path: Path) -> list[FinTSInstitute]: ...
