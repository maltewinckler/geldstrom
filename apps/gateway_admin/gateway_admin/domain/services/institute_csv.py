"""Institute CSV reader abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from gateway_admin.domain.entities.institutes import FinTSInstitute


class InstituteCsvReaderPort(ABC):
    @abstractmethod
    def read(self, path: Path) -> list[FinTSInstitute]: ...
