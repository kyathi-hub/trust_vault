"""
Audit router — checkpoint creation and export.
Admin-only. Checkpoints are signed with HMAC-SHA256.
"""
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.audit.service import verify_chain
from app.auth.dependencies import CurrentUser
from app.config import get_settings
from app.database import DbSession
from app.models.audit import AuditCheckpoint, AuditEvent
from app.models.user import User, UserRole

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/audit", tags=["audit"])


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


class CheckpointResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    from_sequence: int
    to_sequence: int
    chain_head_hash: str
    event_count: int
    created_by: str | None

    model_config = {"from_attributes": True}


@router.post("/checkpoint", response_model=CheckpointResponse, summary="Create signed audit checkpoint (admin)")
async def create_checkpoint(current_user: CurrentUser, db: DbSession) -> CheckpointResponse:
    """
    Create a signed checkpoint of the current audit chain tail.
    Checkpoints are signed with HMAC-SHA256 using app_secret_key.
    Export checkpoints to offline storage for tamper evidence.
    """
    _require_admin(current_user)
    settings = get_settings()

    # Get the last checkpoint to determine range
    last_cp_result = await db.execute(
        select(AuditCheckpoint).order_by(AuditCheckpoint.to_sequence.desc()).limit(1)
    )
    last_cp = last_cp_result.scalar_one_or_none()
    from_seq = (last_cp.to_sequence + 1) if last_cp else 1

    # Get current chain tail
    tail_result = await db.execute(
        select(AuditEvent).order_by(AuditEvent.sequence.desc()).limit(1)
    )
    tail = tail_result.scalar_one_or_none()
    if tail is None or tail.sequence < from_seq:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No new audit events since last checkpoint",
        )

    # Count events in range
    from sqlalchemy import and_, func
    count_result = await db.execute(
        select(func.count()).where(
            and_(AuditEvent.sequence >= from_seq, AuditEvent.sequence <= tail.sequence)
        )
    )
    event_count = count_result.scalar_one()

    # Sign the checkpoint data
    checkpoint_data = {
        "from_sequence": from_seq,
        "to_sequence": tail.sequence,
        "chain_head_hash": tail.event_hash,
        "event_count": event_count,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": str(current_user.id),
    }
    canonical = json.dumps(checkpoint_data, sort_keys=True, separators=(",", ":"))
    signature = hmac.new(
        settings.app_secret_key.encode(),
        canonical.encode(),
        hashlib.sha256,
    ).hexdigest()  # hmac.new(key, msg, digestmod) is correct Python stdlib usage

    cp = AuditCheckpoint(
        from_sequence=from_seq,
        to_sequence=tail.sequence,
        chain_head_hash=tail.event_hash,
        event_count=event_count,
        signature=signature,
        created_by=str(current_user.id),
    )
    db.add(cp)
    await db.flush()

    logger.info(
        "audit_checkpoint_created",
        from_seq=from_seq,
        to_seq=tail.sequence,
        event_count=event_count,
        admin=str(current_user.id),
    )
    return CheckpointResponse.model_validate(cp)


@router.get("/checkpoints", response_model=list[CheckpointResponse], summary="List audit checkpoints (admin)")
async def list_checkpoints(current_user: CurrentUser, db: DbSession) -> list[CheckpointResponse]:
    _require_admin(current_user)
    result = await db.execute(
        select(AuditCheckpoint).order_by(AuditCheckpoint.created_at.desc())
    )
    return [CheckpointResponse.model_validate(cp) for cp in result.scalars().all()]
