"""
Admin router — security dashboard and audit access.
Admin-only. Never returns document content.
"""
import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from app.audit.service import verify_chain
from app.auth.dependencies import CurrentUser
from app.database import DbSession
from app.models.audit import AuditEvent
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


class AuditEventResponse(BaseModel):
    id: str
    sequence: int
    occurred_at: datetime
    actor_id: str | None
    actor_email: str | None
    action: str
    outcome: str
    target_type: str | None
    target_id: str | None
    correlation_id: str | None

    model_config = {"from_attributes": True}


class AuditListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int


class AdminStatsResponse(BaseModel):
    total_documents: int
    total_users: int
    total_audit_events: int
    denied_events_24h: int


@router.get("/stats", response_model=AdminStatsResponse, summary="Admin dashboard stats")
async def get_admin_stats(current_user: CurrentUser, db: DbSession) -> AdminStatsResponse:
    """System-wide stats for admin dashboard. No document content returned."""
    _require_admin(current_user)

    from datetime import UTC, timedelta
    now = datetime.now(UTC)
    day_ago = now - timedelta(hours=24)

    total_docs = (await db.execute(
        select(func.count()).select_from(Document).where(Document.status == "active")
    )).scalar_one()

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()

    total_audit = (await db.execute(select(func.count()).select_from(AuditEvent))).scalar_one()

    denied_24h = (await db.execute(
        select(func.count()).select_from(AuditEvent).where(
            and_(AuditEvent.outcome == "denied", AuditEvent.occurred_at >= day_ago.isoformat())
        )
    )).scalar_one()

    return AdminStatsResponse(
        total_documents=total_docs,
        total_users=total_users,
        total_audit_events=total_audit,
        denied_events_24h=denied_24h,
    )


@router.get("/audit", response_model=AuditListResponse, summary="List audit events (admin)")
async def list_audit_events(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = Query(None),
    outcome: str | None = Query(None),
    actor_id: str | None = Query(None),
    target_id: str | None = Query(None),
    from_time: datetime | None = Query(None),
    to_time: datetime | None = Query(None),
) -> AuditListResponse:
    _require_admin(current_user)

    filters = []
    if action:
        filters.append(AuditEvent.action.ilike(f"%{action}%"))
    if outcome:
        filters.append(AuditEvent.outcome == outcome)
    if actor_id:
        filters.append(AuditEvent.actor_id == actor_id)
    if target_id:
        filters.append(AuditEvent.target_id == target_id)
    if from_time:
        filters.append(AuditEvent.occurred_at >= from_time.isoformat())
    if to_time:
        filters.append(AuditEvent.occurred_at <= to_time.isoformat())

    base_q = select(AuditEvent).order_by(AuditEvent.sequence.desc())
    if filters:
        base_q = base_q.where(and_(*filters))

    total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(base_q.offset(offset).limit(page_size))
    events = result.scalars().all()

    return AuditListResponse(
        items=[AuditEventResponse.model_validate(e) for e in events],
        total=total, page=page, page_size=page_size,
    )


@router.get("/audit/verify", summary="Verify audit chain integrity (admin)")
async def verify_audit_chain(
    current_user: CurrentUser,
    db: DbSession,
    from_sequence: int = Query(1, ge=1),
    to_sequence: int | None = Query(None),
) -> dict:
    _require_admin(current_user)
    return await verify_chain(db, from_sequence=from_sequence, to_sequence=to_sequence)
