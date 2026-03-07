"""Authentication dependency for Admin REST API."""

import os

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()


def get_admin_token() -> str:
    """Get the admin API token from environment variable.

    Raises:
        KeyError: If ADMIN_API_TOKEN is not set.
    """
    return os.environ["ADMIN_API_TOKEN"]


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    expected_token: str = Depends(get_admin_token),
) -> None:
    """Verify the bearer token matches the expected admin token.

    Raises:
        HTTPException: 401 if the token is invalid.
    """
    if credentials.credentials != expected_token:
        raise HTTPException(status_code=401, detail="Invalid token")
