"""Domain error types for the admin CLI bounded context."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-level invariant violations."""


class ValidationError(DomainError):
    """Raised when input data fails domain validation rules."""


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist."""
