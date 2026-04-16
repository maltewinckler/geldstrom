"""Domain repository protocols."""

from .institute_repository import AdminInstituteRepository
from .product_repository import ProductRegistrationRepository
from .user_repository import UserRepository

__all__ = [
    "AdminInstituteRepository",
    "ProductRegistrationRepository",
    "UserRepository",
]
