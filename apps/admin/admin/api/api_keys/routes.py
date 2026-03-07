"""API routes for the api_keys bounded context."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from admin.api.api_keys.schemas import (
    AccountResponse,
    ApiKeySummary,
    CreateAccountRequest,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
)
from admin.api.auth import verify_token
from admin.application.api_keys.use_cases import (
    CreateAccount,
    CreateApiKey,
    DeleteAccount,
    GetAccount,
    RevokeApiKey,
    RotateApiKey,
)

router = APIRouter(
    prefix="/admin", tags=["api_keys"], dependencies=[Depends(verify_token)]
)


def get_create_account() -> CreateAccount:
    """Dependency injection for CreateAccount use case."""
    raise NotImplementedError("Must be overridden at app startup")


def get_get_account() -> GetAccount:
    """Dependency injection for GetAccount use case."""
    raise NotImplementedError("Must be overridden at app startup")


def get_delete_account() -> DeleteAccount:
    """Dependency injection for DeleteAccount use case."""
    raise NotImplementedError("Must be overridden at app startup")


def get_create_api_key() -> CreateApiKey:
    """Dependency injection for CreateApiKey use case."""
    raise NotImplementedError("Must be overridden at app startup")


def get_revoke_api_key() -> RevokeApiKey:
    """Dependency injection for RevokeApiKey use case."""
    raise NotImplementedError("Must be overridden at app startup")


def get_rotate_api_key() -> RotateApiKey:
    """Dependency injection for RotateApiKey use case."""
    raise NotImplementedError("Must be overridden at app startup")


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    request: CreateAccountRequest,
    use_case: CreateAccount = Depends(get_create_account),
) -> AccountResponse:
    """Create a new account."""
    account = await use_case.execute(request.account_id)
    return AccountResponse(
        account_id=account.id,
        created_at=account.created_at,
        api_keys=[],
    )


@router.get(
    "/accounts/{account_id}",
    response_model=AccountResponse,
)
async def get_account(
    account_id: UUID,
    use_case: GetAccount = Depends(get_get_account),
) -> AccountResponse:
    """Retrieve an account with its API key summaries."""
    account, api_keys = await use_case.execute(account_id)
    return AccountResponse(
        account_id=account.id,
        created_at=account.created_at,
        api_keys=[
            ApiKeySummary(
                key_id=key.id,
                status=key.status,
                created_at=key.created_at,
            )
            for key in api_keys
        ],
    )


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_account(
    account_id: UUID,
    use_case: DeleteAccount = Depends(get_delete_account),
) -> Response:
    """Delete an account."""
    await use_case.execute(account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api-keys",
    response_model=CreateApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    request: CreateApiKeyRequest,
    use_case: CreateApiKey = Depends(get_create_api_key),
) -> CreateApiKeyResponse:
    """Create a new API key for an account.

    Returns the raw key exactly once. Store it securely.
    """
    key_id, raw_key = await use_case.execute(request.account_id)
    return CreateApiKeyResponse(
        key_id=key_id,
        raw_key=raw_key.value.get_secret_value(),
    )


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_api_key(
    key_id: UUID,
    use_case: RevokeApiKey = Depends(get_revoke_api_key),
) -> Response:
    """Revoke an API key."""
    await use_case.execute(key_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api-keys/{key_id}/rotate",
    response_model=CreateApiKeyResponse,
)
async def rotate_api_key(
    key_id: UUID,
    use_case: RotateApiKey = Depends(get_rotate_api_key),
) -> CreateApiKeyResponse:
    """Rotate an API key.

    Revokes the old key and creates a new one atomically.
    Returns the new raw key exactly once.
    """
    new_key_id, raw_key = await use_case.execute(key_id)
    return CreateApiKeyResponse(
        key_id=new_key_id,
        raw_key=raw_key.value.get_secret_value(),
    )
