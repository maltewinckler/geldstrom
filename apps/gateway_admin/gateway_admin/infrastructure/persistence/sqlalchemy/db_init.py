"""Idempotent database initialisation for the admin service."""

from __future__ import annotations

import logging

from gateway_contracts.schema import metadata
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from gateway_admin.config import Settings

logger = logging.getLogger(__name__)


def _quote_ident(s: str) -> str:
    return '"' + s.replace('"', '""') + '"'


def _quote_literal(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


async def initialize_database(settings: Settings) -> None:
    """Ensure the database, tables, and gateway DB user exist.

    Creates the database, schema tables, and the restricted gateway DB user if
    they do not already exist. Safe to call on every startup - all operations
    use ``IF NOT EXISTS`` semantics or explicit existence checks.
    """
    maintenance_engine = create_async_engine(
        settings.maintenance_url, isolation_level="AUTOCOMMIT"
    )
    try:
        async with maintenance_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": settings.postgres_db},
            )
        if not exists:
            async with maintenance_engine.connect() as conn:
                await conn.execute(
                    text(f"CREATE DATABASE {_quote_ident(settings.postgres_db)}")
                )
            logger.info("Created database '%s'.", settings.postgres_db)
        else:
            logger.debug("Database '%s' already exists.", settings.postgres_db)
    finally:
        await maintenance_engine.dispose()

    app_engine = create_async_engine(settings.database_url)
    try:
        async with app_engine.begin() as conn:
            await conn.run_sync(metadata.create_all, checkfirst=True)
            logger.debug("Schema tables verified/created.")

            # Create the delete-prevention trigger on audit_events (idempotent).
            # CREATE OR REPLACE FUNCTION handles the function side; the trigger
            # itself has no IF NOT EXISTS syntax, so we guard with a pg_trigger check.
            await conn.execute(
                text(
                    """
                    CREATE OR REPLACE FUNCTION prevent_audit_delete()
                    RETURNS TRIGGER LANGUAGE plpgsql AS $$
                    BEGIN
                        RAISE EXCEPTION 'Deletion from audit_events is not permitted';
                    END;
                    $$
                    """
                )
            )
            trigger_exists = await conn.scalar(
                text("SELECT 1 FROM pg_trigger WHERE tgname = 'audit_events_no_delete'")
            )
            if not trigger_exists:
                await conn.execute(
                    text(
                        "CREATE TRIGGER audit_events_no_delete "
                        "BEFORE DELETE ON audit_events "
                        "FOR EACH ROW EXECUTE FUNCTION prevent_audit_delete()"
                    )
                )
                logger.info("Created audit_events delete-prevention trigger.")
            else:
                logger.debug("audit_events delete-prevention trigger already exists.")

            gw_user = settings.gateway_db_user
            gw_pw = settings.gateway_db_password.get_secret_value()
            qi = _quote_ident(gw_user)

            user_exists = await conn.scalar(
                text("SELECT 1 FROM pg_roles WHERE rolname = :n"), {"n": gw_user}
            )
            if not user_exists:
                await conn.execute(
                    text(
                        f"CREATE ROLE {qi} WITH LOGIN PASSWORD {_quote_literal(gw_pw)}"
                    )
                )
                logger.info("Created gateway DB user '%s'.", gw_user)
            else:
                logger.debug("Gateway DB user '%s' already exists.", gw_user)

            await conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {qi}"))
            await conn.execute(
                text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {qi}")
            )
            await conn.execute(
                text(
                    f"ALTER DEFAULT PRIVILEGES IN SCHEMA public"
                    f" GRANT SELECT ON TABLES TO {qi}"
                )
            )
    finally:
        await app_engine.dispose()

    logger.info("Database initialisation complete.")
