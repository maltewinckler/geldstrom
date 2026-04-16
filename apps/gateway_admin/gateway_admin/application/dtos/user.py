"""User-related result DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from gateway_admin.domain.entities.users import User, UserStatus


@dataclass(frozen=True)
class UserSummary:
    """Sanitized user view for operator-facing flows."""

    user_id: str
    email: str
    status: UserStatus
    created_at: datetime
    rotated_at: datetime | None = None


@dataclass(frozen=True)
class UserKeyResult:
    """Result envelope for create/rotate flows that reveal a raw key once."""

    user: UserSummary
    raw_api_key: str


def to_user_summary(user: User) -> UserSummary:
    return UserSummary(
        user_id=str(user.user_id),
        email=user.email.value,
        status=user.status,
        created_at=user.created_at,
        rotated_at=user.rotated_at,
    )
