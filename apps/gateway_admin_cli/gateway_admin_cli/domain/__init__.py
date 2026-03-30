"""Domain models for the gateway admin CLI."""

from .errors import DomainError, NotFoundError, ValidationError
from .institutes import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
    InstituteSelectionPolicy,
)
from .product import ProductRegistration
from .users import ApiKeyHash, Email, User, UserId, UserStatus

__all__ = [
    "ApiKeyHash",
    "BankLeitzahl",
    "Bic",
    "DomainError",
    "Email",
    "FinTSInstitute",
    "InstituteEndpoint",
    "InstituteSelectionPolicy",
    "NotFoundError",
    "ProductRegistration",
    "User",
    "UserId",
    "UserStatus",
    "ValidationError",
]
