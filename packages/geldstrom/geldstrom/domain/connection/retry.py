"""Abstract retry response for domain layer."""

from __future__ import annotations

from abc import ABCMeta, abstractmethod


class NeedRetryResponse(metaclass=ABCMeta):
    """Base for responses requiring the caller to retry or resume later."""

    @abstractmethod
    def get_data(self) -> bytes: ...


class ResponseStatus:
    """Protocol-agnostic response status levels."""

    UNKNOWN = 0
    SUCCESS = 1
    WARNING = 2
    ERROR = 3
