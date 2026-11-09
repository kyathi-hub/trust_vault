"""DocumentGrant model."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Permission(str, enum.Enum):
    READ = "read"
    EDIT = "edit"


PERMISSION_IMPLIES: dict[Permission, set[Permission]] = {
    Permission.EDIT: {Permission.READ, Permission.EDIT},
    Permission.READ: {Permission.READ},
}


class DocumentGrant(Base):
    __tablename__ = "document_grants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    grantee_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    grantor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    permission: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    revocation_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    document: Mapped["Document"] = relationship("Document", back_populates="grants")  # type: ignore[name-defined]
    grantee: Mapped["User"] = relationship("User", back_populates="grants_received", foreign_keys=[grantee_id])  # type: ignore[name-defined]
    grantor: Mapped["User"] = relationship("User", back_populates="grants_given", foreign_keys=[grantor_id])  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<DocumentGrant doc={self.document_id} grantee={self.grantee_id} perm={self.permission}>"
