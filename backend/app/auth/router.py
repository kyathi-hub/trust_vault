"""
Auth router — user provisioning on first login and current user profile.

The OIDC Authorization Code + PKCE flow is handled entirely by the frontend
and Keycloak. The backend validates tokens and provisions users in the app DB.
"""

from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.auth.jwt import validate_token
from app.database import DbSession
from app.models.user import User, UserRole

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)


class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


@router.post(
    "/provision",
    response_model=UserProfileResponse,
    summary="Provision user on first login",
    description=(
        "Called by the frontend after OIDC login to create the user in the app DB "
        "if they do not exist yet. Idempotent — safe to call on every login. "
        "Updates last_login_at on every call."
    ),
)
async def provision_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: DbSession,
) -> UserProfileResponse:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")

    user = await _provision_user_from_token(credentials.credentials, db)
    return UserProfileResponse.model_validate(user)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
async def get_me(current_user: CurrentUser) -> UserProfileResponse:
    """Returns the authenticated and active user's profile."""
    return UserProfileResponse.model_validate(current_user)


async def _provision_user_from_token(token: str, db: AsyncSession) -> User:
    """
    Validate a Keycloak JWT and provision/update the user in the app DB.
    Role is always set to VIEWER on creation — admins promote via users API.
    Never trusts role claims from the token.
    """
    try:
        claims = await validate_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    subject: str = claims.get("sub", "")
    email: str = claims.get("email", "")
    display_name: str = claims.get("name", "") or claims.get("preferred_username", email)

    if not subject or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing required claims",
        )

    result = await db.execute(select(User).where(User.subject == subject))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            subject=subject,
            email=email,
            display_name=display_name,
            role=UserRole.VIEWER,
            is_active=True,
        )
        db.add(user)
        logger.info("user_provisioned", subject=subject, email=email)
    else:
        user.display_name = display_name
        user.email = email

    user.last_login_at = datetime.now(UTC)
    await db.flush()
    return user
