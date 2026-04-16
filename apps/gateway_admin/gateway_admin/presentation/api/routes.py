"""API route handlers for gateway-admin-ui."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status

from gateway_admin.application.commands.create_user import CreateUserCommand
from gateway_admin.application.commands.delete_user import DeleteUserCommand
from gateway_admin.application.commands.disable_user import DisableUserCommand
from gateway_admin.application.commands.reactivate_user import ReactivateUserCommand
from gateway_admin.application.commands.rotate_user_key import RotateUserKeyCommand
from gateway_admin.application.commands.sync_institute_catalog import (
    SyncInstituteCatalogCommand,
)
from gateway_admin.application.queries.list_users import ListUsersQuery
from gateway_admin.domain.errors import ValidationError
from gateway_admin.infrastructure.services.email_service import EmailServiceError

from .dependencies import RepoFactoryDep, ServiceFactoryDep
from .schemas import (
    CatalogSyncResponse,
    CreateUserRequest,
    CreateUserResponse,
    ErrorResponse,
    UserListResponse,
)
from .schemas import (
    UserSummary as UserSummarySchema,
)

router = APIRouter()


@router.get(
    "/users", response_model=UserListResponse, responses={500: {"model": ErrorResponse}}
)
async def list_users(repo: RepoFactoryDep) -> UserListResponse:
    users = await ListUsersQuery.from_factory(repo)()
    return UserListResponse(
        users=[
            UserSummarySchema.model_validate(u)
            for u in sorted(users, key=lambda u: u.email.lower())
        ]
    )


@router.post(
    "/users",
    response_model=CreateUserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def create_user(
    request: CreateUserRequest,
    repo: RepoFactoryDep,
    svc: ServiceFactoryDep,
) -> CreateUserResponse:
    try:
        result = await CreateUserCommand.from_factory(repo, svc)(request.email)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
            if "already exists" in str(e)
            else status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except EmailServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Email delivery failed: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {e}",
        ) from e
    return CreateUserResponse(
        user=UserSummarySchema.model_validate(result.user),
        message="Token sent to email",
    )


@router.post(
    "/users/{user_id}/reroll",
    response_model=CreateUserResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def reroll_user(
    user_id: str,
    repo: RepoFactoryDep,
    svc: ServiceFactoryDep,
) -> CreateUserResponse:
    try:
        result = await RotateUserKeyCommand.from_factory(repo, svc)(user_id)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if "No user found" in str(e)
            else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except EmailServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Email delivery failed: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reroll token: {e}",
        ) from e
    return CreateUserResponse(
        user=UserSummarySchema.model_validate(result.user),
        message="Token sent to email",
    )


@router.post(
    "/users/{user_id}/disable",
    response_model=UserSummarySchema,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def disable_user(
    user_id: str,
    repo: RepoFactoryDep,
    svc: ServiceFactoryDep,
) -> UserSummarySchema:
    try:
        result = await DisableUserCommand.from_factory(repo, svc)(user_id)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if "No user found" in str(e)
            else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    return UserSummarySchema.model_validate(result)


@router.post(
    "/users/{user_id}/reactivate",
    response_model=CreateUserResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def reactivate_user(
    user_id: str,
    repo: RepoFactoryDep,
    svc: ServiceFactoryDep,
) -> CreateUserResponse:
    try:
        result = await ReactivateUserCommand.from_factory(repo, svc)(user_id)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if "No user found" in str(e)
            else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    return CreateUserResponse(
        user=UserSummarySchema.model_validate(result.user),
        message="Token sent to email",
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def delete_user(
    user_id: str,
    repo: RepoFactoryDep,
    svc: ServiceFactoryDep,
) -> None:
    try:
        await DeleteUserCommand.from_factory(repo, svc)(user_id)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if "No user found" in str(e)
            else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/catalog/sync",
    response_model=CatalogSyncResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def sync_catalog(
    file: UploadFile,
    repo: RepoFactoryDep,
    svc: ServiceFactoryDep,
) -> CatalogSyncResponse:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are accepted.",
        )
    try:
        contents = await file.read()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(contents)
            tmp_path = Path(tmp.name)
        try:
            result = await SyncInstituteCatalogCommand.from_factory(repo, svc)(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Catalog sync failed: {e}",
        ) from e
    return CatalogSyncResponse(
        loaded_count=result.loaded_count,
        skipped_count=len(result.skipped_rows),
    )
