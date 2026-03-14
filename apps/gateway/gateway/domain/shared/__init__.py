"""Shared domain primitives for the gateway backend."""

from .errors import DomainError
from .ids import EntityId
from .protocols import BankProtocol

__all__ = ["BankProtocol", "DomainError", "EntityId"]
