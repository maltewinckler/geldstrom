"""Pydantic schemas for API request/response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from gateway_admin.domain.entities.users import UserStatus


class UserSummary(BaseModel):
    """Sanitized user view for API responses."""

    user_id: str = Field(description="Unique identifier for the user")
    email: str = Field(description="User's email address")
    status: UserStatus = Field(description="User's current status")
    created_at: datetime = Field(description="Timestamp when user was created")
    rotated_at: datetime | None = Field(
        default=None, description="Timestamp when API key was last rotated"
    )

    model_config = {"use_enum_values": True, "from_attributes": True}


class CreateUserRequest(BaseModel):
    email: EmailStr = Field(description="Email address for the new user")


class CreateUserResponse(BaseModel):
    user: UserSummary
    message: str


class UserListResponse(BaseModel):
    users: list[UserSummary]


class ErrorResponse(BaseModel):
    detail: str


class CatalogSyncResponse(BaseModel):
    loaded_count: int
    skipped_count: int
