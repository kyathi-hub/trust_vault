"""
Health check endpoints — liveness and readiness.

/health/live  — is the process running? (no DB check)
/health/ready — are all dependencies reachable? (DB + MinIO)

These endpoints reveal NO sensitive configuration or internal details.
They do not require authentication.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.database import get_session_factory

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/live", response_model=LivenessResponse, summary="Liveness check")
async def liveness() -> LivenessResponse:
    """Returns 200 if the process is running."""
    return LivenessResponse(status="ok")


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness check")
async def readiness() -> ReadinessResponse:
    """
    Returns 200 if all required dependencies are reachable.
    Returns 503 if any dependency is unhealthy.
    Does not expose internal configuration.
    """
    from fastapi import HTTPException, status

    checks: dict[str, str] = {}
    all_ok = True

    # Check PostgreSQL
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
        all_ok = False

    # Check storage
    try:
        from app.storage.adapter import health_check
        if health_check():
            checks["storage"] = "ok"
        else:
            checks["storage"] = "unavailable"
            all_ok = False
    except Exception:
        checks["storage"] = "unavailable"
        all_ok = False

    if not all_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ReadinessResponse(status="unavailable", checks=checks).model_dump(),
        )

    return ReadinessResponse(status="ok", checks=checks)
