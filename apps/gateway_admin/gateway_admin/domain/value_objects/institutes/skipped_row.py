"""SkippedRow value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkippedRow:
    """A CSV row that had a valid BLZ but could not be fully parsed."""

    blz: str
    name: str
    reason: str
