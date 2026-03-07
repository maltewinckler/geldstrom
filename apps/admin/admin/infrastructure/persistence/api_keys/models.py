"""ORM models for the api_keys bounded context."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from admin.infrastructure.persistence.database import Base

if TYPE_CHECKING:
    pass


class AccountORM(Base):
    """ORM model for accounts table."""

    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())

    # Relationship to API keys
    api_keys: Mapped[list["ApiKeyORM"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class ApiKeyORM(Base):
    """ORM model for api_keys table."""

    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    key_hash: Mapped[str] = mapped_column(Text)
    sha256_key_hash: Mapped[str] = mapped_column(Text, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    # Relationship to account
    account: Mapped["AccountORM"] = relationship(back_populates="api_keys")
