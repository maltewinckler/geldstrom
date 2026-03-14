"""Result DTO for the resume-pending-operations background command."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResumeSummary:
    """Transition counts produced by one background polling pass."""

    completed_count: int = 0
    failed_count: int = 0
    expired_count: int = 0
    pending_count: int = 0
