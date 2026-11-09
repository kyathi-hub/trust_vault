"""
Test fixtures — creates test DB, test users, and test documents.
All tests use real DB (no mocks of the auth/permission layer).

Test personas:
- alice: owner of doc_a and doc_b
- bob: viewer with read grant on doc_a only
- carol: viewer with no access to any document
- admin: administrator
"""
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.database import Base, get_db
from app.main import app
from app.models.document import Document, DocumentStatus, DocumentVersion, ScanStatus
from app.models.permission import DocumentGrant, Permission
from app.models.user import User, UserRole

# Use in-memory SQLite for tests (fast, no Docker needed for unit tests)
# For integration tests with PostgreSQL, see tests/integration/conftest.py
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with DB override."""
    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ── Test users ────────────────────────────────────────────────────────────────

def make_user(role: UserRole, email: str) -> User:
    return User(
        id=uuid.uuid4(),
        subject=f"subject-{email}",
        email=email,
        display_name=email.split("@")[0].capitalize(),
        role=role,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest_asyncio.fixture
async def alice(db_session: AsyncSession) -> User:
    user = make_user(UserRole.OWNER, "alice@test.local")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def bob(db_session: AsyncSession) -> User:
    user = make_user(UserRole.VIEWER, "bob@test.local")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def carol(db_session: AsyncSession) -> User:
    user = make_user(UserRole.VIEWER, "carol@test.local")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin(db_session: AsyncSession) -> User:
    user = make_user(UserRole.ADMIN, "admin@test.local")
    db_session.add(user)
    await db_session.flush()
    return user


# ── Test documents ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def doc_a(db_session: AsyncSession, alice: User) -> Document:
    """Alice's document A — has a clean version."""
    doc = Document(
        id=uuid.uuid4(),
        owner_id=alice.id,
        display_name="Document A",
        description="Test document A",
        status=DocumentStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(doc)
    await db_session.flush()

    version = DocumentVersion(
        id=uuid.uuid4(),
        document_id=doc.id,
        version_number=1,
        object_key=str(uuid.uuid4()),  # random key — never exposed
        encrypted_dek="dGVzdA==",  # placeholder for unit tests
        kek_version="v1",
        original_filename="document-a.pdf",
        file_size_bytes=1024,
        verified_content_type="application/pdf",
        checksum_sha256="abc123",
        scan_status=ScanStatus.CLEAN,
        uploader_id=alice.id,
        created_at=datetime.now(UTC),
    )
    db_session.add(version)
    await db_session.flush()

    doc.current_version_id = version.id
    await db_session.flush()
    return doc


@pytest_asyncio.fixture
async def doc_b(db_session: AsyncSession, alice: User) -> Document:
    """Alice's document B — no grants to anyone."""
    doc = Document(
        id=uuid.uuid4(),
        owner_id=alice.id,
        display_name="Document B",
        status=DocumentStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


@pytest_asyncio.fixture
async def bob_read_grant_doc_a(
    db_session: AsyncSession, alice: User, bob: User, doc_a: Document
) -> DocumentGrant:
    """Bob has read access to doc_a."""
    grant = DocumentGrant(
        id=uuid.uuid4(),
        document_id=doc_a.id,
        grantee_id=bob.id,
        grantor_id=alice.id,
        permission=Permission.READ,
        created_at=datetime.now(UTC),
    )
    db_session.add(grant)
    await db_session.flush()
    return grant


def make_token_for(user: User) -> str:
    """Return a fake bearer token string that identifies the user for test overrides."""
    return f"test-token-{user.subject}"


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token_for(user)}"}
