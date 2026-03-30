"""PostgreSQL-backed persistence infrastructure."""

from gateway_contracts.schema import create_test_schema, drop_test_schema

from .connection import build_engine
from .consumer_repository import PostgresApiConsumerRepository
from .institute_repository import PostgresFinTSInstituteRepository
from .product_registration_repository import PostgresFinTSProductRegistrationRepository

__all__ = [
    "PostgresApiConsumerRepository",
    "PostgresFinTSInstituteRepository",
    "PostgresFinTSProductRegistrationRepository",
    "build_engine",
    "create_test_schema",
    "drop_test_schema",
]
