"""Runtime settings for the gateway admin CLI."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings for the admin CLI.

    Reads from ``config/admin_cli.env`` (relative to the repository root).
    Superuser credentials use the canonical ``POSTGRES_*`` names so that the
    same file is consumed by both the postgres Docker image and this CLI without
    any duplication.
    """

    model_config = SettingsConfigDict(
        env_file="config/admin_cli.env",
        extra="ignore",
    )

    # Superuser credentials — canonical postgres image variable names
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str = "geldstrom"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Argon2id
    admin_argon2_time_cost: int = 2
    admin_argon2_memory_cost: int = 65_536
    admin_argon2_parallelism: int = 2

    # Gateway app user — different prefix, mapped explicitly
    gateway_db_user: str = Field(validation_alias="GATEWAY_DB_USER")
    gateway_db_password: SecretStr = Field(validation_alias="GATEWAY_DB_PASSWORD")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        from urllib.parse import quote

        pw = quote(self.postgres_password.get_secret_value(), safe="")
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{pw}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def maintenance_url(self) -> str:
        """URL pointing to the 'postgres' maintenance database (for CREATE DATABASE)."""
        from urllib.parse import quote

        pw = quote(self.postgres_password.get_secret_value(), safe="")
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{pw}"
            f"@{self.postgres_host}:{self.postgres_port}/postgres"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
