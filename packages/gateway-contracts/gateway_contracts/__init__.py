"""Shared contracts between the Geldstrom gateway and admin CLI."""

from .channels import (
    CATALOG_REPLACED_CHANNEL,
    CONSUMER_UPDATED_CHANNEL,
    PRODUCT_REGISTRATION_UPDATED_CHANNEL,
)
from .schema import (
    api_consumers_table,
    create_test_schema,
    drop_test_schema,
    fints_institutes_table,
    fints_product_registration_table,
    metadata,
)

__all__ = [
    "CATALOG_REPLACED_CHANNEL",
    "CONSUMER_UPDATED_CHANNEL",
    "PRODUCT_REGISTRATION_UPDATED_CHANNEL",
    "api_consumers_table",
    "create_test_schema",
    "drop_test_schema",
    "fints_institutes_table",
    "fints_product_registration_table",
    "metadata",
]
