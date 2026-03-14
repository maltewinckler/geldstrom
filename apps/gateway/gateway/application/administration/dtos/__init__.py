"""Result DTOs for the administration bounded context."""

from .api_consumer import ApiConsumerKeyResult, ApiConsumerSummary, to_consumer_summary
from .backend_state import BackendStateReport
from .institute_catalog import InstituteCatalogSyncResult
from .product_registration import (
    ProductRegistrationSummary,
    to_product_registration_summary,
)

__all__ = [
    "ApiConsumerKeyResult",
    "ApiConsumerSummary",
    "BackendStateReport",
    "InstituteCatalogSyncResult",
    "ProductRegistrationSummary",
    "to_consumer_summary",
    "to_product_registration_summary",
]


__all__ = [
    "ApiConsumerKeyResult",
    "ApiConsumerSummary",
    "BackendStateReport",
    "InstituteCatalogSyncResult",
    "ProductRegistrationSummary",
    "to_consumer_summary",
    "to_product_registration_summary",
]
