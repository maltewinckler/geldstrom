"""Time and identifier provider abstractions for application use cases."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class IdProvider(Protocol):
    """Provides stable timestamps and operation identifiers to use cases."""

    def new_operation_id(self) -> str: ...

    def now(self) -> datetime: ...
