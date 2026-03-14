"""Shared protocol-related enums and value types."""

from enum import Enum


class BankProtocol(str, Enum):
    """Externally selectable banking protocols supported by the gateway."""

    FINTS = "fints"
