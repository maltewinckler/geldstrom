"""Runtime settings for the gateway admin CLI."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings for the admin CLI.

    Reads from ``config/admin_cli.env`` (relative to the repository root).
    Admin-specific variables carry the ``ADMIN_`` prefix; the gateway DB user
    variables use ``GATEWAY_`` so they can be copy-pasted into ``gateway.env``.
    """

    model_config = SettingsConfigDict(
        env_file="config/admin_cli.env",
        env_prefix="ADMIN_",
        extra="ignore",
    )

    # Admin/owner DB credentials (ADMIN_ prefix via env_prefix)
    db_user: str
    db_password: SecretStr
    db_name: str
    db_host: str = "localhost"
    db_port: int = 5432

    # Argon2id (ADMIN_ prefix via env_prefix)
    argon2_time_cost: int = 2
    argon2_memory_cost: int = 65_536
    argon2_parallelism: int = 2

    # Gateway app user — different prefix, mapped explicitly
    gateway_db_user: str = Field(validation_alias="GATEWAY_DB_USER")
    gateway_db_password: SecretStr = Field(validation_alias="GATEWAY_DB_PASSWORD")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        from urllib.parse import quote

        pw = quote(self.db_password.get_secret_value(), safe="")
        return (
            f"postgresql+asyncpg://{self.db_user}:{pw}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def maintenance_url(self) -> str:
        """URL pointing to the 'postgres' maintenance database (for CREATE DATABASE)."""
        from urllib.parse import quote

        pw = quote(self.db_password.get_secret_value(), safe="")
        return (
            f"postgresql+asyncpg://{self.db_user}:{pw}"
            f"@{self.db_host}:{self.db_port}/postgres"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
