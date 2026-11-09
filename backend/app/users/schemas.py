"""Pydantic schemas for user API responses."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.user import UserRole


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Admin-only: update role or active status. display_name auto-synced from Keycloak."""
    role: UserRole | None = None
    is_active: bool | None = None
