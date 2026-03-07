"""ORM models for the bank_directory bounded context."""

from sqlalchemy import LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from admin.infrastructure.persistence.database import Base


class BankEndpointORM(Base):
    """ORM model for bank_endpoints table."""

    __tablename__ = "bank_endpoints"

    bank_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    protocol: Mapped[str] = mapped_column(String(20))
    server_url: Mapped[str] = mapped_column(Text)
    protocol_config_encrypted: Mapped[bytes] = mapped_column(
        LargeBinary
    )  # Fernet-encrypted JSON
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )  # Use metadata_ to avoid conflict with SQLAlchemy's metadata
