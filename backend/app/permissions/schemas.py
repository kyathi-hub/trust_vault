"""Pydantic schemas for permission grants."""
import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.permission import Permission


class GrantResponse(BaseModel):
    id: str
    document_id: str
    grantee_id: str
    grantor_id: str
    permission: str
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    revocation_reason: str

    model_config = {"from_attributes": True}


class GrantCreateRequest(BaseModel):
    grantee_id: str  # Accept as string to avoid UUID formatting issues
    permission: Permission
    expires_at: datetime | None = None


class GrantRevokeRequest(BaseModel):
    reason: str = ""
