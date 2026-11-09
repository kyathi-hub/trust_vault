"""
Dev-only utilities — approve quarantined uploads for testing.
Only active when dev_auth_enabled=True (never in production).
"""
import uuid

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.auth.dependencies import CurrentUser
from app.config import get_settings
from app.database import DbSession
from app.models.document import DocumentVersion, ScanStatus

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/dev", tags=["dev-utils"])


@router.post("/documents/{document_id}/approve-scan", summary="Mark document as scan-clean (dev only)")
async def approve_scan(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    DEV ONLY — marks all versions of a document as CLEAN so they can be downloaded.
    Simulates ClamAV passing the scan. Not available in production.
    """
    if not get_settings().dev_auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    result = await db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == str(document_id))
    )
    versions = result.scalars().all()
    if not versions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    for v in versions:
        v.scan_status = ScanStatus.CLEAN.value

    logger.info("dev_scan_approved", document_id=str(document_id), versions=len(versions))
    return {"approved": len(versions), "document_id": str(document_id)}
