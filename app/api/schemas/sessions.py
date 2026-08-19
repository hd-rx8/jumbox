from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    expires_in_seconds: int = Field(default=1800, ge=0, le=604800)
    burn_after_download: bool = False


class CreateSessionResponse(BaseModel):
    session_id: UUID
    session_code: str
    status: str
    expires_at: datetime | None = None
    burn_after_download: bool = False


class InitResumableItemRequest(BaseModel):
    original_name: str
    total_size_bytes: int = Field(..., ge=0)
    expected_sha256: str | None = None


class OffsetResponse(BaseModel):
    item_id: UUID
    bytes_received: int
    total_size_bytes: int
    status: str


class ChunkUploadResponse(BaseModel):
    item_id: UUID
    bytes_received: int
    total_size_bytes: int
    completed: bool
    checksum_sha256: str | None = None
    status: str


class TransferItemResponse(BaseModel):
    item_id: UUID
    session_id: UUID
    original_name: str
    size_bytes: int
    checksum_sha256: str | None = None
    status: str
    error_message: str | None = None


class SessionDetailResponse(BaseModel):
    session_id: UUID
    session_code: str
    status: str
    expires_at: datetime | None = None
    burn_after_download: bool = False
    download_count: int = 0
    total_size_bytes: int
    items: list[TransferItemResponse]
    created_at: datetime


class SessionSummaryResponse(BaseModel):
    session_id: UUID
    session_code: str
    status: str
    expires_at: datetime | None = None
    burn_after_download: bool = False
    download_count: int = 0
    total_size_bytes: int
    item_count: int
    created_at: datetime

