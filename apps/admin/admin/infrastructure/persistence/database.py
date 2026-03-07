"""SQLAlchemy async database configuration."""

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


def get_database_url() -> str:
    """Get the database URL from environment variable."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return database_url


# Create async engine with pool_pre_ping for connection health checks
engine = create_async_engine(
    get_database_url(),
    pool_pre_ping=True,
)

# Session factory for creating async sessions
AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
)
