"""Abstract retry response for domain layer."""
from __future__ import annotations

from abc import ABCMeta, abstractmethod


class NeedRetryResponse(metaclass=ABCMeta):
    """
    Base class for responses that require the caller to retry or continue later.

    This is the protocol-agnostic domain concept. Concrete implementations
    (e.g., FinTS TAN flows) add serialization and protocol-specific fields
    in infrastructure.
    """

    @abstractmethod
    def get_data(self) -> bytes:
        """Return an opaque blob that can be used to resume this response."""


class ResponseStatus:
    """
    Generic response status levels.

    These are protocol-agnostic categories; mapping from protocol-specific
    codes happens in infrastructure.
    """

    UNKNOWN = 0
    SUCCESS = 1
    WARNING = 2
    ERROR = 3
