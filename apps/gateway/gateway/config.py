"""Runtime settings for the gateway backend."""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed runtime settings for the gateway backend."""

    model_config = SettingsConfigDict(
        env_prefix="GATEWAY_",
        env_file=".env",
        extra="ignore",
    )

    database_url: SecretStr
    product_master_key: SecretStr
    argon2_time_cost: int = 2
    argon2_memory_cost: int = 65_536
    argon2_parallelism: int = 2
    operation_session_ttl_seconds: int = 120
    operation_session_max_count: int = 10_000
    rate_limit_requests_per_minute: int = 60
    notify_reconnect_backoff_seconds: float = 1.0
    fints_product_version: str = "1.0.0"
    product_key_version: str = "v1"
