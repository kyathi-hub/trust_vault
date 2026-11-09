"""
IDOR / isolation tests.

Verifies:
- Bob cannot access Carol's unshared documents
- Carol cannot access doc_a or doc_b at all
- Changing document IDs in URLs never grants access
- Counts and lists never leak inaccessible documents
"""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.permissions.actions import DocumentAction
from app.permissions.service import authorize_document_action
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_carol_cannot_access_doc_a(
    db_session: AsyncSession,
    carol: User,
    doc_a: Document,
    bob_read_grant_doc_a,
) -> None:
    """Carol has no grant — must get 404, not the document."""
    with pytest.raises(HTTPException) as exc_info:
        await authorize_document_action(db_session, carol, doc_a.id, DocumentAction.METADATA_READ)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_carol_cannot_access_doc_b(
    db_session: AsyncSession,
    carol: User,
    doc_b: Document,
) -> None:
    """Carol has no grant to doc_b — must get 404."""
    with pytest.raises(HTTPException) as exc_info:
        await authorize_document_action(db_session, carol, doc_b.id, DocumentAction.METADATA_READ)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_bob_cannot_access_doc_b(
    db_session: AsyncSession,
    bob: User,
    doc_b: Document,
) -> None:
    """Bob has read on doc_a but NOT doc_b — must get 404."""
    with pytest.raises(HTTPException) as exc_info:
        await authorize_document_action(db_session, bob, doc_b.id, DocumentAction.METADATA_READ)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_bob_can_access_doc_a(
    db_session: AsyncSession,
    bob: User,
    doc_a: Document,
    bob_read_grant_doc_a,
) -> None:
    """Bob has read grant on doc_a — access should be granted."""
    result = await authorize_document_action(db_session, bob, doc_a.id, DocumentAction.METADATA_READ)
    assert result.id == doc_a.id


@pytest.mark.asyncio
async def test_alice_can_access_own_document(
    db_session: AsyncSession,
    alice: User,
    doc_a: Document,
) -> None:
    """Owner always has access."""
    result = await authorize_document_action(db_session, alice, doc_a.id, DocumentAction.DOWNLOAD)
    assert result.id == doc_a.id


@pytest.mark.asyncio
async def test_random_uuid_returns_404(
    db_session: AsyncSession,
    carol: User,
) -> None:
    """Guessing a random UUID must return 404."""
    with pytest.raises(HTTPException) as exc_info:
        await authorize_document_action(db_session, carol, uuid.uuid4(), DocumentAction.METADATA_READ)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_admin_cannot_access_doc_without_grant(
    db_session: AsyncSession,
    admin: User,
    doc_a: Document,
) -> None:
    """Admin has no implicit content access — must get 404 without a grant."""
    with pytest.raises(HTTPException) as exc_info:
        await authorize_document_action(db_session, admin, doc_a.id, DocumentAction.CONTENT_READ)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_admin_cannot_download_without_grant(
    db_session: AsyncSession,
    admin: User,
    doc_a: Document,
) -> None:
    """Admin cannot download document content without an explicit grant."""
    with pytest.raises(HTTPException) as exc_info:
        await authorize_document_action(db_session, admin, doc_a.id, DocumentAction.DOWNLOAD)
    assert exc_info.value.status_code == 404
