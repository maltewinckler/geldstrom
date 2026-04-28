"""Result DTOs for the admin CLI."""

from gateway_admin.application.dtos.backend_state import BackendStateReport
from gateway_admin.application.dtos.institute_catalog import InstituteCatalogSyncResult
from gateway_admin.application.dtos.product_registration import (
    ProductRegistrationSummary,
    to_product_registration_summary,
)
from gateway_admin.application.dtos.user import (
    UserKeyResult,
    UserSummary,
    to_user_summary,
)

__all__ = [
    "BackendStateReport",
    "InstituteCatalogSyncResult",
    "ProductRegistrationSummary",
    "UserKeyResult",
    "UserSummary",
    "to_product_registration_summary",
    "to_user_summary",
]
