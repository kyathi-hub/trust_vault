"""User model."""
import enum
import uuid
from datetime import datetime, UTC

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OWNER = "owner"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owned_documents: Mapped[list["Document"]] = relationship(  # type: ignore[name-defined]
        "Document", back_populates="owner", foreign_keys="Document.owner_id"
    )
    grants_received: Mapped[list["DocumentGrant"]] = relationship(  # type: ignore[name-defined]
        "DocumentGrant", back_populates="grantee", foreign_keys="DocumentGrant.grantee_id"
    )
    grants_given: Mapped[list["DocumentGrant"]] = relationship(  # type: ignore[name-defined]
        "DocumentGrant", back_populates="grantor", foreign_keys="DocumentGrant.grantor_id"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
