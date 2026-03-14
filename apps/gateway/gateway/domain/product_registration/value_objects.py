"""Value objects for product registration secrets."""

from __future__ import annotations

from dataclasses import dataclass

from gateway.domain.shared import DomainError


@dataclass(frozen=True)
class EncryptedProductKey:
    """Encrypted shared FinTS product key material."""

    value: bytes

    def __post_init__(self) -> None:
        if not self.value:
            raise DomainError("EncryptedProductKey must not be empty")


@dataclass(frozen=True)
class ProductVersion:
    """Version string of the registered shared FinTS product."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise DomainError("ProductVersion must not be empty")


@dataclass(frozen=True)
class KeyVersion:
    """Version string of the encrypted key material."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise DomainError("KeyVersion must not be empty")
