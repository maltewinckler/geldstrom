"""SQLAlchemy-backed persistence infrastructure."""

from gateway_contracts.schema import create_test_schema, drop_test_schema

from gateway.infrastructure.persistence.sqlalchemy.audit_repository import (
    AuditRepositorySqlAlchemy,
)
from gateway.infrastructure.persistence.sqlalchemy.connection import build_engine
from gateway.infrastructure.persistence.sqlalchemy.consumer_repository import (
    ApiConsumerRepositorySqlAlchemy,
)
from gateway.infrastructure.persistence.sqlalchemy.institute_repository import (
    FinTSInstituteRepositorySqlAlchemy,
)
from gateway.infrastructure.persistence.sqlalchemy.product_registration_repository import (
    FinTSProductRegistrationRepositorySqlAlchemy,
)

__all__ = [
    "AuditRepositorySqlAlchemy",
    "ApiConsumerRepositorySqlAlchemy",
    "FinTSInstituteRepositorySqlAlchemy",
    "FinTSProductRegistrationRepositorySqlAlchemy",
    "build_engine",
    "create_test_schema",
    "drop_test_schema",
]
