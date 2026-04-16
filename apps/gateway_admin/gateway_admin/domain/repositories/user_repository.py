"""Repository protocol for users (API consumers)."""

from __future__ import annotations

from typing import Protocol

from gateway_admin.domain.entities.users import User
from gateway_admin.domain.value_objects.user import Email, UserId


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UserId) -> User | None: ...

    async def get_by_email(self, email: Email) -> User | None: ...

    async def save(self, user: User) -> None: ...

    async def list_all(self) -> list[User]: ...
