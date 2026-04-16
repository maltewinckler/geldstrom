"""Identity and time provider abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class IdProvider(ABC):
    @abstractmethod
    def new_operation_id(self) -> str: ...

    @abstractmethod
    def now(self) -> datetime: ...
