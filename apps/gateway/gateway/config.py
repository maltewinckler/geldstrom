"""Runtime settings for the gateway backend."""

from __future__ import annotations

from urllib.parse import quote

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed runtime settings for the gateway backend."""

    model_config = SettingsConfigDict(
        env_prefix="GATEWAY_",
        env_file="config/gateway.env",
        extra="ignore",
    )

    # ── Database connection (components, so Docker can override only the host) ──
    db_user: str = "gateway"
    db_password: SecretStr
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "geldstrom"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> SecretStr:
        pw = quote(self.db_password.get_secret_value(), safe="")
        return SecretStr(
            f"postgresql+asyncpg://{self.db_user}:{pw}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # ── Argon2id key hashing ────────────────────────────────────────────────────
    argon2_time_cost: int = 2
    argon2_memory_cost: int = 65_536
    argon2_parallelism: int = 2
    # ── Operation sessions ──────────────────────────────────────────────────────
    operation_session_ttl_seconds: int = 120
    operation_session_max_count: int = 10_000
    # ── Rate limiting ───────────────────────────────────────────────────────────
    rate_limit_requests_per_minute: int = 60
    # ── PostgreSQL NOTIFY reconnect ─────────────────────────────────────────────
    notify_reconnect_backoff_seconds: float = 1.0
    # ── FinTS product ───────────────────────────────────────────────────────────
    fints_product_version: str = "1.0.0"
