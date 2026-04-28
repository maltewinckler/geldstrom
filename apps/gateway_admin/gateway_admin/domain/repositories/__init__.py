"""Domain repository protocols."""

from gateway_admin.domain.repositories.institute_repository import (
    AdminInstituteRepository,
)
from gateway_admin.domain.repositories.product_repository import (
    ProductRegistrationRepository,
)
from gateway_admin.domain.repositories.user_repository import UserRepository

__all__ = [
    "AdminInstituteRepository",
    "ProductRegistrationRepository",
    "UserRepository",
]
