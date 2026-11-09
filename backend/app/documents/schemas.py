"""Pydantic schemas for document API."""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.models.document import DocumentStatus, ScanStatus


class DocumentVersionResponse(BaseModel):
    id: uuid.UUID
    version_number: int
    original_filename: str
    file_size_bytes: int
    verified_content_type: str
    checksum_sha256: str
    scan_status: ScanStatus
    created_at: datetime
    # object_key is NEVER included in responses

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    description: str
    status: DocumentStatus
    owner_id: uuid.UUID
    category_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    current_version: DocumentVersionResponse | None = None

    model_config = {"from_attributes": True}


class DocumentCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=500)
    description: str = Field("", max_length=5000)
    category_id: uuid.UUID | None = None

    @field_validator("display_name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        # Strip null bytes and leading/trailing whitespace
        cleaned = v.replace("\x00", "").strip()
        if not cleaned:
            raise ValueError("display_name cannot be empty or only whitespace")
        return cleaned


class DocumentUpdateRequest(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)
    category_id: uuid.UUID | None = None

    @field_validator("display_name")
    @classmethod
    def sanitize_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        cleaned = v.replace("\x00", "").strip()
        if not cleaned:
            raise ValueError("display_name cannot be empty or only whitespace")
        return cleaned


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
