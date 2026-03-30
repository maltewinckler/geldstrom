"""Deterministic fake time and id provider for application tests."""

from __future__ import annotations

from datetime import datetime, timedelta


class FakeIdProvider:
    """Returns predictable timestamps and operation identifiers."""

    def __init__(
        self,
        *,
        now_value: datetime,
        operation_ids: list[str] | None = None,
    ) -> None:
        self._now_value = now_value
        self._operation_ids = list(operation_ids or ["op-1"])

    def new_operation_id(self) -> str:
        if not self._operation_ids:
            raise AssertionError("No fake operation ids remaining")
        return self._operation_ids.pop(0)

    def now(self) -> datetime:
        return self._now_value

    def advance(self, *, seconds: int = 0, minutes: int = 0) -> None:
        self._now_value = self._now_value + timedelta(seconds=seconds, minutes=minutes)
