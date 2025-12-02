"""Shared utilities for example scripts.

This module provides common functionality used across all examples:
- Environment file loading
- Client creation
- Output formatting
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from geldstrom import FinTS3Client


def load_env(path: str | Path = ".env") -> dict[str, str]:
    """Load environment variables from a .env file.

    Args:
        path: Path to .env file (default: ".env")

    Returns:
        Dictionary of environment variables

    Raises:
        FileNotFoundError: If the .env file doesn't exist
    """
    env_path = Path(path)
    if not env_path.exists():
        raise FileNotFoundError(
            f"Environment file '{env_path}' not found.\n"
            "Create a .env file with your bank credentials."
        )

    env: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        # Strip quotes from value
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        env[key.strip()] = value

    # OS environment variables override .env file
    for key, value in os.environ.items():
        if key.startswith("FINTS_"):
            env[key] = value

    return env


def require_env(env: dict[str, str], key: str) -> str:
    """Get a required environment variable.

    Args:
        env: Environment dictionary
        key: Variable name

    Returns:
        Variable value

    Raises:
        RuntimeError: If variable is missing
    """
    value = env.get(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def create_client(env: dict[str, str], **kwargs) -> FinTS3Client:
    """Create a FinTS3Client from environment variables.

    Args:
        env: Environment dictionary from load_env()
        **kwargs: Additional arguments to pass to FinTS3Client

    Returns:
        Configured FinTS3Client instance
    """
    return FinTS3Client(
        bank_code=require_env(env, "FINTS_BLZ"),
        server_url=require_env(env, "FINTS_SERVER"),
        user_id=require_env(env, "FINTS_USER"),
        pin=require_env(env, "FINTS_PIN"),
        product_id=require_env(env, "FINTS_PRODUCT_ID"),
        country_code=env.get("FINTS_COUNTRY", "DE"),
        customer_id=env.get("FINTS_CUSTOMER_ID"),
        tan_medium=env.get("FINTS_TAN_MEDIUM"),
        tan_method=env.get("FINTS_TAN_METHOD"),
        **kwargs,
    )


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to an argument parser.

    Args:
        parser: ArgumentParser to add arguments to
    """
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file (default: .env)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for example scripts.

    Args:
        verbose: If True, enable DEBUG level logging
    """
    import logging

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    if verbose:
        logging.getLogger("geldstrom").setLevel(logging.DEBUG)


def print_header(title: str, width: int = 60) -> None:
    """Print a formatted section header."""
    print("=" * width)
    print(title)
    print("=" * width)


def print_separator(width: int = 60) -> None:
    """Print a separator line."""
    print("-" * width)


def print_footer(width: int = 60) -> None:
    """Print a formatted footer."""
    print("=" * width)

