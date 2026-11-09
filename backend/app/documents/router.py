"""
Documents router — all document CRUD and download endpoints.
Every endpoint enforces server-side authorization.
"""
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response

from app.auth.dependencies import CurrentUser
from app.database import DbSession
from app.documents import service
from app.documents.schemas import (
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


def _correlation_id(request: Request) -> str | None:
    return request.headers.get("X-Correlation-ID")


@router.get("", response_model=DocumentListResponse, summary="List accessible documents")
async def list_documents(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
) -> DocumentListResponse:
    return await service.list_documents(db, current_user, page=page, page_size=page_size, sort_by=sort_by)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, summary="Upload document")
async def upload_document(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    display_name: str = Form(...),
    description: str = Form(""),
    category_id: str | None = Form(None),
) -> DocumentResponse:
    from app.models.user import UserRole
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    meta = DocumentCreateRequest(
        display_name=display_name,
        description=description,
        category_id=uuid.UUID(category_id) if category_id else None,
    )
    return await service.upload_document(
        db, current_user, meta, file, correlation_id=_correlation_id(request)
    )


@router.get("/{document_id}", response_model=DocumentResponse, summary="Get document metadata")
async def get_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentResponse:
    return await service.get_document(db, current_user, document_id, correlation_id=_correlation_id(request))


@router.patch("/{document_id}", response_model=DocumentResponse, summary="Update document metadata")
async def update_document(
    document_id: uuid.UUID,
    body: DocumentUpdateRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentResponse:
    return await service.update_document_metadata(
        db, current_user, document_id, body, correlation_id=_correlation_id(request)
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft-delete document")
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    await service.delete_document(db, current_user, document_id, correlation_id=_correlation_id(request))


@router.post("/{document_id}/restore", response_model=DocumentResponse, summary="Restore deleted document")
async def restore_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentResponse:
    return await service.restore_document(db, current_user, document_id, correlation_id=_correlation_id(request))


@router.get("/{document_id}/download", summary="Download document content")
async def download_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    version: int | None = Query(None, description="Version number (default: current)"),
) -> Response:
    """
    Stream document content after a fresh server-side authorization check.
    Never returns a storage URL — all bytes flow through this endpoint.
    Content-Disposition is always 'attachment' to prevent inline execution.
    """
    plaintext, content_type, original_filename = await service.download_document(
        db, current_user, document_id,
        version_number=version,
        correlation_id=_correlation_id(request),
    )

    # Safe filename encoding for Content-Disposition
    import urllib.parse
    safe_filename = urllib.parse.quote(original_filename)

    return Response(
        content=plaintext,
        media_type="application/octet-stream",
        headers={
            # Always attachment — never inline — prevents XSS via uploaded files
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
            "X-Content-Type-Options": "nosniff",
            "Content-Length": str(len(plaintext)),
        },
    )
