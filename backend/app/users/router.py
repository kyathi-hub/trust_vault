"""
Users router — admin-only user management.
Regular users cannot call these endpoints.
Role and active-status changes are audited.
"""
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.audit.service import record_event
from app.auth.dependencies import CurrentUser
from app.database import DbSession
from app.models.user import User, UserRole
from app.users.schemas import UserResponse, UserUpdateRequest

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(current_user: User) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


@router.get("", response_model=list[UserResponse], summary="List all users (admin)")
async def list_users(current_user: CurrentUser, db: DbSession) -> list[UserResponse]:
    _require_admin(current_user)
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.get("/grantable", response_model=list[UserResponse], summary="List users available for grants (owner+)")
async def list_grantable_users(current_user: CurrentUser, db: DbSession) -> list[UserResponse]:
    """Any authenticated owner or admin can list active users to grant document access."""
    from app.models.user import UserRole
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    result = await db.execute(
        select(User).where(User.is_active == True).order_by(User.display_name)  # noqa: E712
    )
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.get("/{user_id}", response_model=UserResponse, summary="Get user (admin)")
async def get_user(user_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> UserResponse:
    _require_admin(current_user)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse, summary="Update user role/status (admin)")
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    _require_admin(current_user)

    # Prevent admin from changing their own role (accidental lockout)
    if user_id == current_user.id and body.role is not None and body.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    changes: dict[str, object] = {}
    if body.role is not None and body.role != user.role:
        changes["role"] = {"old": user.role, "new": body.role}
        user.role = body.role
    if body.is_active is not None and body.is_active != user.is_active:
        changes["is_active"] = {"old": user.is_active, "new": body.is_active}
        user.is_active = body.is_active

    if changes:
        await record_event(
            db=db, actor=current_user, action="user:updated", outcome="success",
            target_type="user", target_id=str(user_id),
            metadata={"changes": changes},
            fail_closed=True,
        )

    return UserResponse.model_validate(user)
