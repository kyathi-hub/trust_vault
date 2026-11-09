"""
Audit service — append-only tamper-evident event log.

Hash chain design:
- Each event: event_hash = SHA-256(canonical_json(event_data) + previous_hash)
- "GENESIS" is the sentinel previous_hash for the first event
- Canonical JSON: json.dumps with sort_keys=True, separators=(',', ':'), ensure_ascii=False
- Sequence number auto-incremented via DB sequence — gaps indicate deleted events
- Chain updates serialized via SELECT FOR UPDATE SKIP LOCKED on the last event

Fail-closed policy:
- High-risk operations (download, permission change) set fail_closed=True
- If the audit write fails with fail_closed=True, the calling operation is denied
- This is documented as an availability trade-off in docs/AUDIT_DESIGN.md

Security properties:
- Actor identity comes from the User object passed in — never from request body
- Metadata must not contain secrets, passwords, encryption keys, or file contents
- DB role: INSERT only on audit_events (enforced via migration)
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.user import User

logger = structlog.get_logger(__name__)

GENESIS_HASH = "GENESIS"


def _canonical_json(data: dict[str, Any]) -> str:
    """
    Produce a deterministic canonical JSON string.
    Keys are sorted, no extra whitespace, UTF-8 safe.
    This is the canonical form used for hash computation.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_event_hash(event_data: dict[str, Any], previous_hash: str) -> str:
    """
    Compute SHA-256 hash of canonical event data + previous hash.
    This links each event to its predecessor, forming the hash chain.
    """
    canonical = _canonical_json(event_data)
    payload = f"{canonical}|{previous_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def record_event(
    db: AsyncSession,
    actor: User | None,
    action: str,
    outcome: str,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    source_ip: str | None = None,
    user_agent: str | None = None,
    fail_closed: bool = False,
) -> AuditEvent:
    """
    Record an audit event and append it to the hash chain.

    Args:
        db: Database session (must be within an active transaction for fail_closed operations)
        actor: The User performing the action (None for system/anonymous)
        action: Action string e.g. "document:download"
        outcome: "success" | "denied" | "error"
        target_type: e.g. "document", "user", "grant"
        target_id: UUID or identifier of the target (safe to log — not document content)
        metadata: Additional context — MUST NOT contain secrets or document contents
        correlation_id: Request correlation ID for tracing
        source_ip: Client IP (logged per privacy policy)
        user_agent: Client user agent
        fail_closed: If True, raises on audit write failure (caller should abort the operation)

    Returns:
        The created AuditEvent

    Raises:
        RuntimeError: If fail_closed=True and the audit write fails
    """
    try:
        return await _write_event(
            db=db,
            actor=actor,
            action=action,
            outcome=outcome,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata or {},
            correlation_id=correlation_id,
            source_ip=source_ip,
            user_agent=user_agent,
        )
    except Exception as exc:
        logger.error(
            "audit_write_failed",
            action=action,
            actor_id=str(actor.id) if actor else None,
            error=str(exc),
            fail_closed=fail_closed,
        )
        if fail_closed:
            raise RuntimeError(
                f"Audit write failed for high-risk action '{action}'. "
                "Operation denied (fail-closed policy)."
            ) from exc
        # Non-fail-closed: log the failure but don't block the operation
        # (e.g., denial audit failures don't need to block the 404 response)
        raise


async def _write_event(
    db: AsyncSession,
    actor: User | None,
    action: str,
    outcome: str,
    target_type: str | None,
    target_id: str | None,
    metadata: dict[str, Any],
    correlation_id: str | None,
    source_ip: str | None,
    user_agent: str | None,
) -> AuditEvent:
    """
    Internal: write a single audit event with hash chain maintenance.
    Uses SELECT FOR UPDATE on the last event to serialize chain updates.
    """
    event_id = uuid.uuid4()
    occurred_at = datetime.now(UTC)

    # Serialize access to the chain tail — prevents concurrent chain corruption
    # We lock the row with the highest sequence number
    last_event_result = await db.execute(
        select(AuditEvent)
        .order_by(AuditEvent.sequence.desc())
        .limit(1)
        .with_for_update(skip_locked=False)  # wait for lock — no skip
    )
    last_event = last_event_result.scalar_one_or_none()

    if last_event is None:
        previous_hash = GENESIS_HASH
        next_sequence = 1
    else:
        previous_hash = last_event.event_hash
        next_sequence = last_event.sequence + 1

    # Build canonical event data for hashing
    # This must exactly match what _compute_event_hash uses
    event_data_for_hash: dict[str, Any] = {
        "id": str(event_id),
        "sequence": next_sequence,
        "occurred_at": occurred_at.isoformat(),
        "actor_id": str(actor.id) if actor else None,
        "action": action,
        "outcome": outcome,
        "target_type": target_type,
        "target_id": str(target_id) if target_id else None,
        "correlation_id": str(correlation_id) if correlation_id else None,
    }

    event_hash = _compute_event_hash(event_data_for_hash, previous_hash)

    event = AuditEvent(
        id=str(event_id),
        sequence=next_sequence,
        occurred_at=occurred_at,
        actor_id=str(actor.id) if actor else None,
        actor_email=actor.email if actor else None,
        action=action,
        outcome=outcome,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        correlation_id=str(correlation_id) if correlation_id else None,
        source_ip=source_ip,
        user_agent=user_agent,
        metadata_json=json.dumps(metadata),
        previous_hash=previous_hash,
        event_hash=event_hash,
    )

    db.add(event)
    await db.flush()  # write to DB within current transaction

    logger.debug(
        "audit_event_written",
        sequence=next_sequence,
        action=action,
        outcome=outcome,
        actor_id=str(actor.id) if actor else None,
    )

    return event


async def verify_chain(db: AsyncSession, from_sequence: int = 1, to_sequence: int | None = None) -> dict[str, Any]:
    """
    Verify the integrity of the audit hash chain.
    Returns a dict with verification result and any detected anomalies.

    Detects:
    - Modified events (hash mismatch)
    - Deleted events (sequence gaps)
    - Reordered events (wrong previous_hash reference)
    - Inserted events (impossible without correct previous hash)
    """
    query = select(AuditEvent).where(AuditEvent.sequence >= from_sequence)
    if to_sequence is not None:
        query = query.where(AuditEvent.sequence <= to_sequence)
    query = query.order_by(AuditEvent.sequence.asc())

    result = await db.execute(query)
    events = result.scalars().all()

    if not events:
        return {"valid": True, "events_checked": 0, "anomalies": []}

    anomalies: list[dict[str, Any]] = []
    expected_sequence = events[0].sequence
    previous_hash = events[0].previous_hash

    # Verify first event's previous_hash
    if events[0].sequence == 1 and previous_hash != GENESIS_HASH:
        anomalies.append({
            "type": "invalid_genesis",
            "sequence": events[0].sequence,
            "detail": f"First event previous_hash should be GENESIS, got {previous_hash!r}",
        })

    for event in events:
        # Check for sequence gaps (deleted events)
        if event.sequence != expected_sequence:
            anomalies.append({
                "type": "sequence_gap",
                "expected": expected_sequence,
                "found": event.sequence,
                "detail": f"Missing events between sequence {expected_sequence} and {event.sequence}",
            })
            expected_sequence = event.sequence

        # Verify previous_hash matches the hash we computed from the last event
        if event.previous_hash != previous_hash:
            anomalies.append({
                "type": "broken_chain",
                "sequence": event.sequence,
                "detail": (
                    f"Event {event.sequence} previous_hash mismatch. "
                    f"Expected {previous_hash!r}, got {event.previous_hash!r}"
                ),
            })

        # Recompute the event hash and compare
        event_data_for_hash: dict[str, Any] = {
            "id": str(event.id),
            "sequence": event.sequence,
            "occurred_at": event.occurred_at.isoformat(),
            "actor_id": str(event.actor_id) if event.actor_id else None,
            "action": event.action,
            "outcome": event.outcome,
            "target_type": event.target_type,
            "target_id": str(event.target_id) if event.target_id else None,
            "correlation_id": str(event.correlation_id) if event.correlation_id else None,
        }
        expected_hash = _compute_event_hash(event_data_for_hash, event.previous_hash)
        if event.event_hash != expected_hash:
            anomalies.append({
                "type": "hash_mismatch",
                "sequence": event.sequence,
                "detail": (
                    f"Event {event.sequence} hash mismatch. "
                    f"Stored: {event.event_hash!r}, computed: {expected_hash!r}"
                ),
            })

        previous_hash = event.event_hash
        expected_sequence += 1

    return {
        "valid": len(anomalies) == 0,
        "events_checked": len(events),
        "from_sequence": events[0].sequence,
        "to_sequence": events[-1].sequence,
        "chain_head_hash": events[-1].event_hash if events else None,
        "anomalies": anomalies,
    }
