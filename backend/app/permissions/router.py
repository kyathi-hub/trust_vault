"""
Permissions router — document grant management.
Only the document owner can create or revoke grants.
All UUID values converted to strings for SQLite compatibility.
"""
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import and_, select

from app.audit.service import record_event
from app.auth.dependencies import CurrentUser
from app.database import DbSession
from app.models.document import Document, DocumentStatus
from app.models.permission import DocumentGrant, Permission
from app.models.user import User
from app.permissions.actions import DocumentAction
from app.permissions.schemas import GrantCreateRequest, GrantResponse, GrantRevokeRequest
from app.permissions.service import authorize_document_action

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/documents/{document_id}/grants", tags=["grants"])


def _cid(request: Request) -> str | None:
    return request.headers.get("X-Correlation-ID")


@router.get("", response_model=list[GrantResponse], summary="List grants (owner only)")
async def list_grants(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> list[GrantResponse]:
    await authorize_document_action(db, current_user, document_id, DocumentAction.GRANT_LIST, correlation_id=_cid(request))
    result = await db.execute(
        select(DocumentGrant)
        .where(DocumentGrant.document_id == str(document_id))
        .order_by(DocumentGrant.created_at.desc())
    )
    return [GrantResponse.model_validate(g) for g in result.scalars().all()]


@router.post("", response_model=GrantResponse, status_code=status.HTTP_201_CREATED, summary="Create grant (owner only)")
async def create_grant(
    document_id: uuid.UUID,
    body: GrantCreateRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> GrantResponse:
    # Only owner can grant
    await authorize_document_action(db, current_user, document_id, DocumentAction.SHARE, correlation_id=_cid(request))

    grantee_id_str = str(body.grantee_id)
    grantor_id_str = str(current_user.id)

    # Prevent self-grant
    if grantee_id_str == grantor_id_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot grant access to yourself")

    # Verify grantee exists and is active
    grantee_result = await db.execute(
        select(User).where(and_(User.id == grantee_id_str, User.is_active == True))  # noqa: E712
    )
    grantee = grantee_result.scalar_one_or_none()
    if grantee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    perm_value = body.permission.value if hasattr(body.permission, "value") else str(body.permission)

    # Check for duplicate active grant
    existing = await db.execute(
        select(DocumentGrant).where(
            and_(
                DocumentGrant.document_id == str(document_id),
                DocumentGrant.grantee_id == grantee_id_str,
                DocumentGrant.permission == perm_value,
                DocumentGrant.revoked_at.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An active grant already exists")

    grant = DocumentGrant(
        document_id=str(document_id),
        grantee_id=grantee_id_str,
        grantor_id=grantor_id_str,
        permission=perm_value,
        expires_at=body.expires_at,
    )
    db.add(grant)
    await db.flush()

    await record_event(
        db=db, actor=current_user, action="grant:created", outcome="success",
        target_type="document_grant", target_id=str(grant.id),
        metadata={
            "document_id": str(document_id),
            "grantee_id": grantee_id_str,
            "permission": perm_value,
            "expires_at": body.expires_at.isoformat() if body.expires_at else None,
        },
        correlation_id=_cid(request),
        fail_closed=True,
    )

    return GrantResponse.model_validate(grant)


@router.delete("/{grant_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke grant (owner only)")
async def revoke_grant(
    document_id: uuid.UUID,
    grant_id: uuid.UUID,
    body: GrantRevokeRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    await authorize_document_action(db, current_user, document_id, DocumentAction.REVOKE, correlation_id=_cid(request))

    result = await db.execute(
        select(DocumentGrant).where(
            and_(
                DocumentGrant.id == str(grant_id),
                DocumentGrant.document_id == str(document_id),
                DocumentGrant.revoked_at.is_(None),
            )
        )
    )
    grant = result.scalar_one_or_none()
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")

    grant.revoked_at = datetime.now(UTC)
    grant.revocation_reason = body.reason

    await record_event(
        db=db, actor=current_user, action="grant:revoked", outcome="success",
        target_type="document_grant", target_id=str(grant_id),
        metadata={
            "document_id": str(document_id),
            "grantee_id": str(grant.grantee_id),
            "permission": str(grant.permission),
            "reason": body.reason,
        },
        correlation_id=_cid(request),
        fail_closed=True,
    )
