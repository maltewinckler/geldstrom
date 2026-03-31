"""SQL-backed persistence infrastructure."""

from gateway_contracts.schema import create_test_schema, drop_test_schema

from .connection import build_engine
from .consumer_repository import SQLApiConsumerRepository
from .institute_repository import SQLFinTSInstituteRepository
from .product_registration_repository import SQLFinTSProductRegistrationRepository

__all__ = [
    "SQLApiConsumerRepository",
    "SQLFinTSInstituteRepository",
    "SQLFinTSProductRegistrationRepository",
    "build_engine",
    "create_test_schema",
    "drop_test_schema",
]
