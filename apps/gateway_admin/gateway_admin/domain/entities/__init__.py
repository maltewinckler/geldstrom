"""Domain entities."""

from gateway_admin.domain.entities.institutes import (
    FinTSInstitute,
    InstituteSelectionPolicy,
)
from gateway_admin.domain.entities.product import ProductRegistration
from gateway_admin.domain.entities.users import User, UserStatus

__all__ = [
    "FinTSInstitute",
    "InstituteSelectionPolicy",
    "ProductRegistration",
    "User",
    "UserStatus",
]
