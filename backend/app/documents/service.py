"""
Document service — business logic for document operations.
All operations go through authorize_document_action() before any data access.
"""
import hashlib
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.audit.service import record_event
from app.config import get_settings
from app.documents.schemas import (
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentVersionResponse,
)
from app.documents.upload_validation import validate_upload
from app.models.document import Document, DocumentStatus, DocumentVersion, ScanStatus
from app.models.permission import DocumentGrant, Permission
from app.models.user import User, UserRole
from app.permissions.actions import DocumentAction
from app.permissions.service import authorize_document_action
from app.storage.encryption import decrypt_dek, encrypt_data, encrypt_dek, generate_dek
from app.storage.adapter import (
    delete_object,
    generate_object_key,
    get_object_bytes,
    put_object,
)

logger = structlog.get_logger(__name__)

# Allowed sort fields — validated against this list to prevent injection
ALLOWED_SORT_FIELDS = {"created_at", "updated_at", "display_name"}
PAGE_SIZE_MAX = 100


async def list_documents(
    db: AsyncSession,
    actor: User,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
) -> DocumentListResponse:
    """
    List documents accessible to the actor.
    Scoped to: documents owned by actor OR documents with active grants to actor.
    Never returns documents the actor cannot access.
    """
    if sort_by not in ALLOWED_SORT_FIELDS:
        sort_by = "created_at"
    page_size = min(page_size, PAGE_SIZE_MAX)
    offset = (page - 1) * page_size

    sort_col = getattr(Document, sort_by)
    now = datetime.now(UTC)

    owned_q = select(Document.id).where(
        and_(Document.owner_id == str(actor.id), Document.status == DocumentStatus.ACTIVE.value)
    )
    granted_q = (
        select(DocumentGrant.document_id)
        .join(Document, Document.id == DocumentGrant.document_id)
        .where(
            and_(
                DocumentGrant.grantee_id == str(actor.id),
                DocumentGrant.revoked_at.is_(None),
                (DocumentGrant.expires_at.is_(None)) | (DocumentGrant.expires_at > now),
                Document.status == DocumentStatus.ACTIVE.value,
            )
        )
    )

    accessible_ids = owned_q.union(granted_q).subquery()

    base_q = (
        select(Document)
        .where(Document.id.in_(select(accessible_ids)))
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


async def get_document(
    db: AsyncSession,
    actor: User,
    document_id: uuid.UUID,
    correlation_id: str | None = None,
) -> DocumentResponse:
    doc = await authorize_document_action(
        db, actor, document_id, DocumentAction.METADATA_READ,
        correlation_id=correlation_id,
    )
    await db.refresh(doc, ["versions"])
    await record_event(
        db=db, actor=actor, action="document:metadata_read", outcome="success",
        target_type="document", target_id=str(document_id),
        correlation_id=correlation_id,
    )
    return _to_response(doc)


async def upload_document(
    db: AsyncSession,
    actor: User,
    metadata: DocumentCreateRequest,
    file: UploadFile,
    correlation_id: str | None = None,
) -> DocumentResponse:
    """
    Upload a new document.
    Owner is always set from the authenticated actor — never from request body.
    Validates file content before storing.
    Encrypts file with per-object DEK before writing to MinIO.
    """
    settings = get_settings()

    # Read file content
    content = await file.read()
    original_filename = file.filename or "untitled"
    claimed_content_type = file.content_type or "application/octet-stream"

    # Validate upload (magic bytes, extension, size, etc.)
    validation = validate_upload(original_filename, content, claimed_content_type)
    if not validation.ok:
        await record_event(
            db=db, actor=actor, action="document:upload_rejected", outcome="denied",
            target_type="document", target_id=None,
            metadata={"reason": validation.error, "filename_length": len(original_filename)},
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Upload rejected: {validation.error}",
        )

    # Generate encryption keys
    dek = generate_dek()
    encrypted_dek = encrypt_dek(dek)
    encrypted_content = encrypt_data(content, dek)

    # Generate random object key — never the original filename
    object_key = generate_object_key()

    # Write to MinIO
    try:
        put_object(object_key, encrypted_content, "application/octet-stream")
    except Exception as exc:
        logger.error("upload_storage_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage error. Please try again.",
        ) from exc

    # Determine scan status
    scan_status = ScanStatus.PENDING
    if not settings.clamav_enabled:
        # ClamAV not available — quarantine file until manually cleared
        scan_status = ScanStatus.SKIPPED

    # Create DB records
    doc = Document(
        owner_id=str(actor.id),
        display_name=metadata.display_name,
        description=metadata.description,
        category_id=str(metadata.category_id) if metadata.category_id else None,
        status=DocumentStatus.ACTIVE.value,
    )
    db.add(doc)
    await db.flush()

    version = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        object_key=object_key,
        encrypted_dek=encrypted_dek,
        kek_version=settings.encryption_kek_version,
        original_filename=original_filename,
        file_size_bytes=validation.file_size,
        verified_content_type=validation.detected_mime or "application/octet-stream",
        checksum_sha256=validation.checksum_sha256 or "",
        scan_status=scan_status.value,
        uploader_id=str(actor.id),
    )
    db.add(version)
    await db.flush()

    doc.current_version_id = version.id
    await db.flush()

    await record_event(
        db=db, actor=actor, action="document:uploaded", outcome="success",
        target_type="document", target_id=str(doc.id),
        metadata={
            "filename_length": len(original_filename),
            "file_size_bytes": validation.file_size,
            "content_type": validation.detected_mime,
            "scan_status": scan_status,
            "version": 1,
        },
        correlation_id=correlation_id,
        fail_closed=True,
    )

    await db.refresh(doc, ["versions"])
    return _to_response(doc)


async def download_document(
    db: AsyncSession,
    actor: User,
    document_id: uuid.UUID,
    version_number: int | None = None,
    correlation_id: str | None = None,
) -> tuple[bytes, str, str]:
    """
    Download document content.

    CRITICAL PATH — security design:
    1. authorize_document_action() — fresh permission check
    2. Verify version is downloadable (scan status = CLEAN)
    3. Audit event written BEFORE streaming (fail_closed=True)
    4. Retrieve encrypted bytes from MinIO
    5. Decrypt with per-object DEK
    6. Return (plaintext_bytes, content_type, filename)

    Object key is fetched from DB — never from client.
    """
    # Step 1: authorization (raises 404 if unauthorized)
    doc = await authorize_document_action(
        db, actor, document_id, DocumentAction.DOWNLOAD,
        correlation_id=correlation_id,
    )

    # Step 2: get the version to download
    await db.refresh(doc, ["versions"])
    if version_number is not None:
        version = next((v for v in doc.versions if v.version_number == version_number), None)
    else:
        # Default: current active version
        version = next((v for v in doc.versions if v.id == doc.current_version_id), None)
        if version is None and doc.versions:
            version = max(doc.versions, key=lambda v: v.version_number)

    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Step 3: verify scan status — quarantined files cannot be downloaded
    if not version.is_downloadable:
        await record_event(
            db=db, actor=actor, action="document:download_blocked", outcome="denied",
            target_type="document", target_id=str(document_id),
            metadata={"reason": "scan_status", "scan_status": version.scan_status},
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document is not available for download",
        )

    # Step 4: write audit BEFORE retrieving file (fail-closed)
    await record_event(
        db=db, actor=actor, action="document:download", outcome="success",
        target_type="document", target_id=str(document_id),
        metadata={"version": version.version_number},
        correlation_id=correlation_id,
        fail_closed=True,  # deny download if audit fails
    )

    # Step 5: retrieve and decrypt
    try:
        encrypted_bytes = get_object_bytes(version.object_key)
        dek = decrypt_dek(version.encrypted_dek)
        plaintext = _decrypt_data_checked(encrypted_bytes, dek, version.checksum_sha256)
    except Exception as exc:
        logger.error("download_decryption_failed", document_id=str(document_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document",
        ) from exc

    return plaintext, version.verified_content_type, version.original_filename


async def update_document_metadata(
    db: AsyncSession,
    actor: User,
    document_id: uuid.UUID,
    body: DocumentUpdateRequest,
    correlation_id: str | None = None,
) -> DocumentResponse:
    doc = await authorize_document_action(
        db, actor, document_id, DocumentAction.EDIT_METADATA,
        correlation_id=correlation_id,
    )
    changes: dict[str, object] = {}
    if body.display_name is not None and body.display_name != doc.display_name:
        changes["display_name"] = {"old": doc.display_name, "new": body.display_name}
        doc.display_name = body.display_name
    if body.description is not None:
        doc.description = body.description
    if body.category_id is not None:
        doc.category_id = body.category_id

    if changes:
        await record_event(
            db=db, actor=actor, action="document:metadata_updated", outcome="success",
            target_type="document", target_id=str(document_id),
            metadata={"changes": changes},
            correlation_id=correlation_id,
            fail_closed=True,
        )
    await db.refresh(doc, ["versions"])
    return _to_response(doc)


async def delete_document(
    db: AsyncSession,
    actor: User,
    document_id: uuid.UUID,
    correlation_id: str | None = None,
) -> None:
    doc = await authorize_document_action(
        db, actor, document_id, DocumentAction.DELETE,
        correlation_id=correlation_id,
    )
    doc.status = DocumentStatus.DELETED.value
    doc.deleted_at = datetime.now(UTC)
    await record_event(
        db=db, actor=actor, action="document:deleted", outcome="success",
        target_type="document", target_id=str(document_id),
        correlation_id=correlation_id,
        fail_closed=True,
    )


async def restore_document(
    db: AsyncSession,
    actor: User,
    document_id: uuid.UUID,
    correlation_id: str | None = None,
) -> DocumentResponse:
    # For restore, we need to find the deleted document — use a direct query
    result = await db.execute(
        select(Document).where(
            and_(Document.id == str(document_id), Document.status == DocumentStatus.DELETED.value)
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None or doc.owner_id != str(actor.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc.status = DocumentStatus.ACTIVE.value
    doc.deleted_at = None
    await record_event(
        db=db, actor=actor, action="document:restored", outcome="success",
        target_type="document", target_id=str(document_id),
        correlation_id=correlation_id,
        fail_closed=True,
    )
    await db.refresh(doc, ["versions"])
    return _to_response(doc)


def _to_response(doc: Document) -> DocumentResponse:
    current_version = None
    if doc.versions:
        active = next((v for v in doc.versions if v.id == doc.current_version_id), None)
        if active is None:
            active = max(doc.versions, key=lambda v: v.version_number)
        if active:
            current_version = DocumentVersionResponse.model_validate(active)
    return DocumentResponse(
        id=doc.id,
        display_name=doc.display_name,
        description=doc.description,
        status=doc.status,
        owner_id=doc.owner_id,
        category_id=doc.category_id,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        current_version=current_version,
    )


def _decrypt_data_checked(encrypted: bytes, dek: bytes, expected_checksum: str) -> bytes:
    from app.storage.encryption import decrypt_data
    plaintext = decrypt_data(encrypted, dek)
    # Verify integrity against stored checksum
    actual = hashlib.sha256(plaintext).hexdigest()
    if actual != expected_checksum:
        raise ValueError(f"Checksum mismatch: stored={expected_checksum!r} actual={actual!r}")
    return plaintext
