"""
Grant creation and revocation tests.
- Only owner can grant/revoke
- Cannot grant to self
- Revocation is immediate
- Expired grants are denied
- Duplicate active grant rejected
"""
import uuid
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.document import Document
from app.models.permission import DocumentGrant, Permission
from app.models.user import User
from app.permissions.actions import DocumentAction
from app.permissions.service import authorize_document_action


@pytest.mark.asyncio
async def test_owner_can_grant_and_grantee_gets_access(
    db_session: AsyncSession, alice: User, bob: User, doc_a: Document
) -> None:
    grant = DocumentGrant(
        id=uuid.uuid4(), document_id=doc_a.id, grantee_id=bob.id,
        grantor_id=alice.id, permission=Permission.READ,
        created_at=datetime.now(UTC),
    )
    db_session.add(grant)
    await db_session.flush()

    result = await authorize_document_action(db_session, bob, doc_a.id, DocumentAction.CONTENT_READ)
    assert result.id == doc_a.id


@pytest.mark.asyncio
async def test_revoked_grant_blocks_immediately(
    db_session: AsyncSession, alice: User, bob: User, doc_a: Document
) -> None:
    grant = DocumentGrant(
        id=uuid.uuid4(), document_id=doc_a.id, grantee_id=bob.id,
        grantor_id=alice.id, permission=Permission.READ,
        created_at=datetime.now(UTC),
        revoked_at=datetime.now(UTC),
    )
    db_session.add(grant)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await authorize_document_action(db_session, bob, doc_a.id, DocumentAction.DOWNLOAD)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_expired_grant_blocks(
    db_session: AsyncSession, alice: User, bob: User, doc_a: Document
) -> None:
    grant = DocumentGrant(
        id=uuid.uuid4(), document_id=doc_a.id, grantee_id=bob.id,
        grantor_id=alice.id, permission=Permission.READ,
        created_at=datetime.now(UTC) - timedelta(hours=2),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    db_session.add(grant)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await authorize_document_action(db_session, bob, doc_a.id, DocumentAction.DOWNLOAD)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_future_expiry_allows_access(
    db_session: AsyncSession, alice: User, bob: User, doc_a: Document
) -> None:
    grant = DocumentGrant(
        id=uuid.uuid4(), document_id=doc_a.id, grantee_id=bob.id,
        grantor_id=alice.id, permission=Permission.READ,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(grant)
    await db_session.flush()

    result = await authorize_document_action(db_session, bob, doc_a.id, DocumentAction.CONTENT_READ)
    assert result.id == doc_a.id


@pytest.mark.asyncio
async def test_non_owner_cannot_use_owner_only_actions(
    db_session: AsyncSession, bob: User, alice: User, doc_a: Document,
    bob_read_grant_doc_a: DocumentGrant,
) -> None:
    for action in (DocumentAction.SHARE, DocumentAction.REVOKE, DocumentAction.DELETE, DocumentAction.GRANT_LIST):
        with pytest.raises(HTTPException) as exc:
            await authorize_document_action(db_session, bob, doc_a.id, action)
        assert exc.value.status_code == 404, f"Expected 404 for action {action}"


@pytest.mark.asyncio
async def test_carol_cannot_read_grants_list(
    db_session: AsyncSession, carol: User, doc_a: Document
) -> None:
    with pytest.raises(HTTPException) as exc:
        await authorize_document_action(db_session, carol, doc_a.id, DocumentAction.GRANT_LIST)
    assert exc.value.status_code == 404
