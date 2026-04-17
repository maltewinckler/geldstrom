"""Async SQLAlchemy engine helpers for PostgreSQL persistence."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool


def build_engine(database_url: str, *, use_null_pool: bool = False) -> AsyncEngine:
    engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
    if use_null_pool:
        engine_kwargs["poolclass"] = NullPool
    return create_async_engine(database_url, **engine_kwargs)
