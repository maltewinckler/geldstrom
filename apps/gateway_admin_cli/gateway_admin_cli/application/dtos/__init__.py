"""Result DTOs for the admin CLI."""

from .backend_state import BackendStateReport
from .institute_catalog import InstituteCatalogSyncResult
from .product_registration import (
    ProductRegistrationSummary,
    to_product_registration_summary,
)
from .user import UserKeyResult, UserSummary, to_user_summary

__all__ = [
    "BackendStateReport",
    "InstituteCatalogSyncResult",
    "ProductRegistrationSummary",
    "UserKeyResult",
    "UserSummary",
    "to_product_registration_summary",
    "to_user_summary",
]
