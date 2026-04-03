"""Credential loading: CLI flags -> .env file -> interactive prompt."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import typer
from dotenv import load_dotenv


@dataclass
class Creds:
    gateway_url: str
    api_key: str
    blz: str
    user_id: str
    password: str
    tan_method: str | None
    tan_medium: str | None


def load_credentials(
    env_file: Path,
    *,
    gateway_url: str | None,
    api_key: str | None,
    blz: str | None,
    user_id: str | None,
    password: str | None,
    tan_method: str | None,
    tan_medium: str | None,
) -> Creds:
    """Resolve credentials in order: CLI flag → .env → interactive prompt."""
    load_dotenv(env_file, override=False)

    def _get(
        cli_val: str | None,
        env_key: str,
        label: str,
        *,
        secret: bool = False,
        default: str | None = None,
        required: bool = True,
    ) -> str | None:
        if cli_val is not None:
            return cli_val or None
        val = os.getenv(env_key, "")
        if val:
            return val
        if not required:
            return default
        result = typer.prompt(label, default=default or "", hide_input=secret)
        return result or None

    return Creds(
        gateway_url=(
            _get(gateway_url, "GATEWAY_URL", "", required=False)
            or "http://localhost:8000"
        ),
        api_key=(
            api_key
            or os.getenv("GATEWAY_API_KEY")
            or typer.prompt("Gateway API key", default="", hide_input=True)
            or ""
        ),
        blz=_get(blz, "FINTS_BLZ", "BLZ") or "",
        user_id=_get(user_id, "FINTS_USER", "User ID") or "",
        password=_get(password, "FINTS_PIN", "Password", secret=True) or "",
        tan_method=_get(tan_method, "FINTS_TAN_METHOD", "", required=False),
        tan_medium=_get(tan_medium, "FINTS_TAN_MEDIUM", "", required=False),
    )
