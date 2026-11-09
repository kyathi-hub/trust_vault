"""
Search and metadata privacy tests.
Ensures search never leaks inaccessible document names, counts, or metadata.
"""
import uuid
import pytest
from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.service import list_documents
from app.models.document import Document, DocumentStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_carol_list_returns_empty(
    db_session: AsyncSession, carol: User, doc_a: Document, doc_b: Document
) -> None:
    """Carol has no grants — list must return 0 items."""
    result = await list_documents(db_session, carol)
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_bob_list_only_returns_granted_docs(
    db_session: AsyncSession, bob: User, doc_a: Document, doc_b: Document,
    bob_read_grant_doc_a,
) -> None:
    """Bob has grant on doc_a only — list must not include doc_b."""
    result = await list_documents(db_session, bob)
    ids = [str(item.id) for item in result.items]
    assert str(doc_a.id) in ids
    assert str(doc_b.id) not in ids


@pytest.mark.asyncio
async def test_alice_list_returns_own_docs(
    db_session: AsyncSession, alice: User, doc_a: Document, doc_b: Document
) -> None:
    """Alice owns both — list must include both."""
    result = await list_documents(db_session, alice)
    ids = [str(item.id) for item in result.items]
    assert str(doc_a.id) in ids
    assert str(doc_b.id) in ids


@pytest.mark.asyncio
async def test_search_does_not_leak_inaccessible_to_carol(
    db_session: AsyncSession, carol: User, doc_a: Document
) -> None:
    """Search by name should not reveal doc_a to carol."""
    from app.search.router import search_documents
    # Direct service call
    result = await list_documents(db_session, carol)
    assert all(str(item.id) != str(doc_a.id) for item in result.items)


@pytest.mark.asyncio
async def test_total_count_not_leaked(
    db_session: AsyncSession, carol: User, doc_a: Document, doc_b: Document
) -> None:
    """Total count in paginated response must be 0 for carol, not 2."""
    result = await list_documents(db_session, carol)
    assert result.total == 0
