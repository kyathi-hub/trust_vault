"""
Dev-mode authentication — replaces Keycloak OIDC for local testing.

Generates simple signed JWTs for the 4 demo users.
Use the /auth/dev/token endpoint to get a token, then use it as Bearer.

THIS IS ONLY ACTIVE WHEN dev_auth_enabled=True IN SETTINGS.
Never used in production.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel

from app.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth/dev", tags=["dev-auth"])

# Pre-defined demo users — matches seed data in migration 0002
DEV_USERS = {
    "admin": {
        "sub": "demo-admin-subject",
        "email": "admin@trustvault.local",
        "name": "TrustVault Admin",
        "role": "admin",
    },
    "alice": {
        "sub": "demo-alice-subject",
        "email": "alice@trustvault.local",
        "name": "Alice Owner",
        "role": "owner",
    },
    "bob": {
        "sub": "demo-bob-subject",
        "email": "bob@trustvault.local",
        "name": "Bob Viewer",
        "role": "viewer",
    },
    "carol": {
        "sub": "demo-carol-subject",
        "email": "carol@trustvault.local",
        "name": "Carol Viewer",
        "role": "viewer",
    },
}

ALGORITHM = "HS256"


def create_dev_token(username: str) -> str:
    settings = get_settings()
    user = DEV_USERS.get(username)
    if not user:
        raise ValueError(f"Unknown dev user: {username}")

    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user["sub"],
        "email": user["email"],
        "name": user["name"],
        "iss": "trustvault-dev",
        "aud": settings.keycloak_client_id,
        "iat": now,
        "exp": now + timedelta(hours=8),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def validate_dev_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.app_secret_key,
            algorithms=[ALGORITHM],
            audience=settings.keycloak_client_id,
            issuer="trustvault-dev",
            options={"verify_exp": True},
        )
        return claims
    except Exception as exc:
        raise ValueError(f"Invalid dev token: {exc}") from exc


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: str
    email: str
    role: str


@router.get("/token/{username}", response_model=TokenResponse)
async def get_dev_token(username: str) -> TokenResponse:
    """
    Get a dev token for one of the 4 demo users.
    username: admin | alice | bob | carol
    """
    if username not in DEV_USERS:
        raise HTTPException(status_code=404, detail=f"Unknown user. Choose: {', '.join(DEV_USERS)}")
    token = create_dev_token(username)
    user = DEV_USERS[username]
    return TokenResponse(
        access_token=token,
        user=username,
        email=user["email"],
        role=user["role"],
    )


@router.get("/users")
async def list_dev_users() -> list[dict]:
    """List available dev users for testing."""
    return [
        {"username": k, "email": v["email"], "role": v["role"]}
        for k, v in DEV_USERS.items()
    ]
