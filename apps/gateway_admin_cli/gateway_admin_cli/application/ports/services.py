"""Service ports for the admin CLI application layer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol

from gateway_admin_cli.domain.institutes import FinTSInstitute
from gateway_admin_cli.domain.product import ProductRegistration
from gateway_admin_cli.domain.users import ApiKeyHash, User


class AdminApiKeyService(Protocol):
    """Generates and hashes raw API keys for new or rotated credentials."""

    def generate(self) -> str: ...

    def hash(self, raw_key: str) -> ApiKeyHash: ...


class IdProvider(Protocol):
    """Provides stable timestamps and operation identifiers to use cases."""

    def new_operation_id(self) -> str: ...

    def now(self) -> datetime: ...


class InstituteCsvReaderPort(Protocol):
    """Reads raw institute rows from an operator-supplied CSV path."""

    def read(self, path: Path) -> list[FinTSInstitute]: ...


class UserCacheWriter(Protocol):
    """Invalidates the gateway's in-memory user cache for one user."""

    async def reload_one(self, user: User) -> None: ...


class InstituteCacheLoader(Protocol):
    """Signals the gateway to reload its in-memory institute cache."""

    async def load(self, institutes: list[FinTSInstitute]) -> None: ...


class ProductRegistrationNotifier(Protocol):
    """Signals the gateway to reload its product registration cache."""

    async def set_current(self, registration: ProductRegistration | None) -> None: ...
