"""
Central authorization policy service.

THIS IS THE SECURITY BOUNDARY. Every document operation goes through here.

authorize_document_action() checks:
1. actor is authenticated (caller guarantees this via CurrentUser dependency)
2. actor account is active (caller guarantees this via CurrentUser dependency)
3. document exists in the DB
4. document is in an accessible lifecycle state (ACTIVE)
5. actor is the owner OR has an active, unexpired, non-revoked grant
   with a permission level sufficient for the requested action
6. Any additional restrictions (quarantined content, deleted state, etc.)

On authorization failure:
- Returns HTTP 404 (not 403) to avoid revealing resource existence to unauthorized callers
- Internally records an audit event with the denied action BEFORE raising
- Never leaks whether the document exists or belongs to someone else

Security test: tests/security/test_authz_removal.py demonstrates that
removing this call from a download endpoint causes isolation tests to fail.
"""

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.permission import DocumentGrant, Permission
from app.models.user import User, UserRole
from app.permissions.actions import (
    ACTION_REQUIRED_PERMISSION,
    OWNER_ONLY_ACTIONS,
    DocumentAction,
)

logger = structlog.get_logger(__name__)

# Lifecycle states from which a document can be accessed
_ACCESSIBLE_STATUSES = {DocumentStatus.ACTIVE.value}


async def authorize_document_action(
    db: AsyncSession,
    actor: User,
    document_id: uuid.UUID,
    action: DocumentAction,
    *,
    correlation_id: str | None = None,
) -> Document:
    """
    Authorize actor to perform action on document_id.

    Returns the Document ORM object on success.
    Raises HTTP 404 on any failure (authorization or existence).

    IMPORTANT: caller must have already verified actor.is_active via
    the get_current_active_user dependency. This function does not
    re-check is_active to avoid a second DB query per request, but
    it trusts that the dependency chain enforces it.

    The 404 response is intentional: returning 403 would reveal that
    the document exists to an unauthorized caller. We audit the denial
    internally regardless of which error we return to the caller.
    """
    # Fetch document — scoped to ACCESSIBLE statuses only
    result = await db.execute(
        select(Document).where(
            and_(
                Document.id == str(document_id),
                Document.status.in_(_ACCESSIBLE_STATUSES),
            )
        )
    )
    document = result.scalar_one_or_none()

    if document is None:
        # Document does not exist, is deleted/archived/purged, or caller has no access.
        # We return the same 404 in all cases to avoid existence disclosure.
        await _record_denial(
            db=db,
            actor=actor,
            document_id=document_id,
            action=action,
            reason="document_not_found_or_inaccessible",
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check if actor is the owner
    if document.owner_id == str(actor.id):
        logger.debug(
            "authz_granted_owner",
            actor_id=str(actor.id),
            document_id=str(document_id),
            action=action,
        )
        return document

    # Administrators have NO implicit document content access
    # They can only access documents through explicit grants (same as any other user)
    # Exception: admin-specific actions (purge, audit) are handled in their own routers

    # Owner-only actions cannot be performed via grants
    if action in OWNER_ONLY_ACTIONS:
        await _record_denial(
            db=db,
            actor=actor,
            document_id=document_id,
            action=action,
            reason="owner_only_action",
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check for an active, non-revoked, non-expired grant with sufficient permission
    required_perm_str = ACTION_REQUIRED_PERMISSION.get(action)
    if required_perm_str is None:
        # Action requires ownership — already handled above
        await _record_denial(
            db=db,
            actor=actor,
            document_id=document_id,
            action=action,
            reason="owner_only_action",
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    required_perm = Permission(required_perm_str)
    now = datetime.now(UTC)

    # edit grants satisfy both 'edit' and 'read' requirements
    # read grants only satisfy 'read'
    allowed_permissions: list[str] = (
        [Permission.READ.value, Permission.EDIT.value]
        if required_perm == Permission.READ
        else [Permission.EDIT.value]
    )

    grant_result = await db.execute(
        select(DocumentGrant).where(
            and_(
                DocumentGrant.document_id == str(document_id),
                DocumentGrant.grantee_id == str(actor.id),
                DocumentGrant.permission.in_(allowed_permissions),
                DocumentGrant.revoked_at.is_(None),
                (DocumentGrant.expires_at.is_(None)) | (DocumentGrant.expires_at > now),
            )
        ).limit(1)
    )
    grant = grant_result.scalar_one_or_none()

    if grant is None:
        await _record_denial(
            db=db,
            actor=actor,
            document_id=document_id,
            action=action,
            reason="no_active_grant",
            correlation_id=correlation_id,
        )
        # Return 404 — same response as "document not found"
        # This prevents an attacker from knowing whether the document exists
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    logger.debug(
        "authz_granted_via_grant",
        actor_id=str(actor.id),
        document_id=str(document_id),
        action=action,
        grant_id=str(grant.id),
        permission=grant.permission,
    )
    return document


async def _record_denial(
    db: AsyncSession,
    actor: User,
    document_id: uuid.UUID,
    action: DocumentAction,
    reason: str,
    correlation_id: str | None,
) -> None:
    """
    Record an authorization denial in the audit log.
    This is called BEFORE raising the HTTP exception.

    We import audit here (not at module level) to avoid circular imports.
    If audit write fails, we log the error but still raise the 404 —
    denials are not fail-closed (only high-risk success operations are).
    """
    try:
        from app.audit.service import record_event  # noqa: PLC0415
        await record_event(
            db=db,
            actor=actor,
            action=f"{action}_denied",
            outcome="denied",
            target_type="document",
            target_id=str(document_id),
            metadata={"reason": reason},
            correlation_id=correlation_id,
        )
    except Exception as exc:
        # Denial audit failure is logged but does not change the 404 response
        logger.error("denial_audit_write_failed", error=str(exc), action=action)
