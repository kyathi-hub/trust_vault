"""
JWT validation — supports both Keycloak OIDC (production) and dev tokens (development).
Dev mode is active when settings.dev_auth_enabled=True.
"""

import time
from typing import Any

import structlog
from jose import JWTError

from app.config import get_settings

logger = structlog.get_logger(__name__)

_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0


async def validate_token(token: str) -> dict[str, Any]:
    """
    Validate a JWT. In dev mode uses simple HMAC, in production uses Keycloak JWKS.
    Returns decoded claims on success, raises JWTError on failure.
    """
    settings = get_settings()

    if settings.dev_auth_enabled:
        return _validate_dev_token(token)

    return await _validate_keycloak_token(token)


def _validate_dev_token(token: str) -> dict[str, Any]:
    """Validate a dev-mode HS256 JWT."""
    from app.auth.dev_auth import validate_dev_token
    try:
        return validate_dev_token(token)
    except Exception as exc:
        raise JWTError(str(exc)) from exc


async def _validate_keycloak_token(token: str) -> dict[str, Any]:
    """Validate a Keycloak RS256 JWT via JWKS."""
    import httpx
    from jose import jwk, jwt
    from jose.exceptions import ExpiredSignatureError

    settings = get_settings()
    global _jwks_cache, _jwks_fetched_at

    try:
        jwks = await _get_jwks()
    except Exception as exc:
        logger.warning("jwks_fetch_failed", error=str(exc))
        raise JWTError("Unable to fetch signing keys") from exc

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise JWTError(f"Invalid token header: {exc}") from exc

    algorithm = unverified_header.get("alg", "")
    if algorithm != "RS256":
        raise JWTError(f"Unsupported algorithm: {algorithm!r}. Only RS256 accepted.")

    kid = unverified_header.get("kid")
    keys = jwks.get("keys", [])
    matching_keys = [k for k in keys if k.get("kid") == kid] if kid else keys

    if not matching_keys:
        _jwks_fetched_at = 0.0
        try:
            jwks = await _get_jwks()
            keys = jwks.get("keys", [])
            matching_keys = [k for k in keys if k.get("kid") == kid] if kid else keys
        except Exception as exc:
            raise JWTError("JWKS refresh failed") from exc

    if not matching_keys:
        raise JWTError(f"No JWKS key found for kid={kid!r}")

    last_error: JWTError | None = None
    for key_data in matching_keys:
        try:
            public_key = jwk.construct(key_data)
            claims: dict[str, Any] = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=settings.keycloak_issuer,
                audience=settings.keycloak_client_id,
                options={"verify_exp": True, "verify_iss": True, "verify_aud": True},
            )
            return claims
        except ExpiredSignatureError as exc:
            raise JWTError("Token has expired") from exc
        except JWTError as exc:
            last_error = exc
            continue

    raise last_error or JWTError("Token validation failed")


async def _get_jwks() -> dict[str, Any]:
    import httpx
    global _jwks_cache, _jwks_fetched_at
    settings = get_settings()
    now = time.monotonic()
    if _jwks_cache and (now - _jwks_fetched_at) < settings.jwks_cache_ttl_seconds:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(settings.keycloak_jwks_uri)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = now
    return _jwks_cache
