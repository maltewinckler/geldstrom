"""InstituteEndpoint value object."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from gateway_admin.domain.errors import DomainError


@dataclass(frozen=True)
class InstituteEndpoint:
    """PIN/TAN endpoint URL used by the banking connector."""

    value: str

    def __post_init__(self) -> None:
        parsed = urlparse(self.value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise DomainError("InstituteEndpoint must be an https URL")

    def __str__(self) -> str:
        return self.value
