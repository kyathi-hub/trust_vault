"""
FastAPI dependencies for authentication and current user resolution.

Every protected route uses get_current_active_user as a dependency.
This ensures:
1. Token is validated against Keycloak JWKS (signature, issuer, aud, exp, alg)
2. User is looked up in the application DB by subject claim
3. User account is_active is checked — deactivated users are blocked immediately
   regardless of token validity or remaining token lifetime.

Actor identity is NEVER taken from the request body or query params.
"""

from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import validate_token
from app.database import get_db
from app.models.user import User

logger = structlog.get_logger(__name__)

# FastAPI security scheme — extracts Bearer token from Authorization header
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate JWT and return the authenticated User from the application DB.
    Raises HTTP 401 if token is missing, invalid, or expired.
    Raises HTTP 401 if user is not found in the application DB.
    Does NOT check is_active — use get_current_active_user for that.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = await validate_token(credentials.credentials)
    except JWTError as exc:
        logger.warning("jwt_validation_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject: str = claims.get("sub", "")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    result = await db.execute(select(User).where(User.subject == subject))
    user = result.scalar_one_or_none()

    if user is None:
        # User authenticated with Keycloak but not yet provisioned in app DB
        # This can happen on first login — caller should handle via /auth/me endpoint
        logger.warning("user_not_in_app_db", subject=subject)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found. Please complete registration.",
        )

    return user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Returns the current user only if their account is active.
    Deactivated users are blocked on every request, regardless of token validity.

    This is the dependency to use on all protected endpoints.
    """
    if not user.is_active:
        logger.warning("deactivated_user_access_attempt", user_id=str(user.id), email=user.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deactivated",
        )
    return user


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
