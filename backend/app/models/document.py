"""Document and DocumentVersion models."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentStatus(str, enum.Enum):
    ACTIVE   = "active"
    DELETED  = "deleted"
    ARCHIVED = "archived"
    PURGED   = "purged"


class ScanStatus(str, enum.Enum):
    PENDING  = "pending"
    CLEAN    = "clean"
    INFECTED = "infected"
    SKIPPED  = "skipped"
    ERROR    = "error"


DOWNLOADABLE_SCAN_STATUSES = {ScanStatus.CLEAN}


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("categories.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=DocumentStatus.ACTIVE)
    current_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="owned_documents", foreign_keys=[owner_id])  # type: ignore[name-defined]
    versions: Mapped[list["DocumentVersion"]] = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.version_number")
    grants: Mapped[list["DocumentGrant"]] = relationship("DocumentGrant", back_populates="document")  # type: ignore[name-defined]
    category: Mapped["Category | None"] = relationship("Category", back_populates="documents")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Document id={self.id} name={self.display_name!r}>"


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_doc_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    object_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    encrypted_dek: Mapped[str] = mapped_column(Text, nullable=False)
    kek_version: Mapped[str] = mapped_column(String(50), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    verified_content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    scan_status: Mapped[str] = mapped_column(String(50), nullable=False, default=ScanStatus.PENDING)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    uploader_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    document: Mapped["Document"] = relationship("Document", back_populates="versions")
    uploader: Mapped["User"] = relationship("User", foreign_keys=[uploader_id])  # type: ignore[name-defined]

    @property
    def is_downloadable(self) -> bool:
        return self.scan_status in {s.value for s in DOWNLOADABLE_SCAN_STATUSES} and self.is_active

    def __repr__(self) -> str:
        return f"<DocumentVersion doc={self.document_id} v={self.version_number}>"
