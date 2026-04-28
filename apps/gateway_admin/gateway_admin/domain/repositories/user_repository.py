"""Repository protocol for users (API consumers)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from gateway_admin.domain.entities.users import User, UserStatus
from gateway_admin.domain.value_objects.user import Email, UserId


@dataclass(frozen=True)
class UserQuery:
    """Filter and pagination parameters for listing users."""

    email_contains: str | None = None
    status: UserStatus | None = None
    page: int = 1
    page_size: int = 50


@dataclass(frozen=True)
class UserPage:
    """Paginated result of a user query."""

    users: list[User] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UserId) -> User | None: ...

    async def get_by_email(self, email: Email) -> User | None: ...

    async def save(self, user: User) -> None: ...

    async def query(self, q: UserQuery) -> UserPage: ...

    async def list_all(self) -> list[User]: ...
