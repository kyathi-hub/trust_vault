"""
Search router — access-filtered document metadata search.

Security: all queries are scoped to documents the caller can access.
No inaccessible document names, owners, categories, or counts are ever returned.
Sort fields validated against an allowlist to prevent injection.
"""
import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Query, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser
from app.database import DbSession
from app.documents.schemas import DocumentListResponse, DocumentResponse
from app.documents.service import _to_response, ALLOWED_SORT_FIELDS, PAGE_SIZE_MAX
from app.models.document import Document, DocumentStatus
from app.models.permission import DocumentGrant

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.get("/documents", response_model=DocumentListResponse, summary="Search accessible documents")
async def search_documents(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    q: str | None = Query(None, max_length=200, description="Search term (document name)"),
    category_id: uuid.UUID | None = Query(None),
    owner_id: uuid.UUID | None = Query(None),
    created_after: datetime | None = Query(None),
    created_before: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
) -> DocumentListResponse:
    """
    Search documents — results are always scoped to the caller's accessible documents.
    Never leaks existence or metadata of inaccessible documents.
    """
    if sort_by not in ALLOWED_SORT_FIELDS:
        sort_by = "created_at"
    page_size = min(page_size, PAGE_SIZE_MAX)
    offset = (page - 1) * page_size

    from datetime import UTC
    now = datetime.now(UTC)
    from sqlalchemy import func

    # Accessible document IDs (owned or granted)
    owned_ids = select(Document.id).where(
        and_(Document.owner_id == current_user.id, Document.status == DocumentStatus.ACTIVE)
    )
    granted_ids = (
        select(DocumentGrant.document_id)
        .join(Document, Document.id == DocumentGrant.document_id)
        .where(
            and_(
                DocumentGrant.grantee_id == current_user.id,
                DocumentGrant.revoked_at.is_(None),
                (DocumentGrant.expires_at.is_(None)) | (DocumentGrant.expires_at > now),
                Document.status == DocumentStatus.ACTIVE,
            )
        )
    )
    accessible = owned_ids.union(granted_ids).subquery()

    filters = [Document.id.in_(select(accessible))]

    if q:
        # Case-insensitive name search
        filters.append(Document.display_name.ilike(f"%{q}%"))
    if category_id:
        filters.append(Document.category_id == category_id)
    if owner_id:
        # Only return docs by that owner that the caller can access
        filters.append(Document.owner_id == owner_id)
    if created_after:
        filters.append(Document.created_at >= created_after)
    if created_before:
        filters.append(Document.created_at <= created_before)

    sort_col = getattr(Document, sort_by)
    base_q = (
        select(Document)
        .where(and_(*filters))
        .options(selectinload(Document.versions))
        .order_by(sort_col.desc())
    )

    total_result = await db.execute(select(func.count()).select_from(base_q.subquery()))
    total = total_result.scalar_one()

    result = await db.execute(base_q.offset(offset).limit(page_size))
    docs = result.scalars().all()

    return DocumentListResponse(
        items=[_to_response(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )
