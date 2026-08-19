from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class SessionStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ItemStatus(StrEnum):
    QUEUED = "queued"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True, kw_only=True)
class TransferItem:
    session_id: UUID
    original_name: str
    size_bytes: int
    id: UUID = field(default_factory=uuid4)
    stored_name: str | None = None
    storage_path: str | None = None
    checksum_sha256: str | None = None
    status: ItemStatus = ItemStatus.QUEUED
    error_message: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def mark_uploading(self) -> None:
        self.status = ItemStatus.UPLOADING
        self.updated_at = _utcnow()

    def mark_completed(self, *, checksum_sha256: str, storage_path: str, stored_name: str | None = None) -> None:
        self.status = ItemStatus.COMPLETED
        self.checksum_sha256 = checksum_sha256
        self.storage_path = storage_path
        if stored_name:
            self.stored_name = stored_name
        self.updated_at = _utcnow()

    def mark_failed(self, error: str) -> None:
        self.status = ItemStatus.FAILED
        self.error_message = error
        self.updated_at = _utcnow()


@dataclass(kw_only=True)
class TransferSession:
    owner_id: UUID
    session_code: str
    id: UUID = field(default_factory=uuid4)
    expires_at: datetime | None = None
    burn_after_download: bool = False
    download_count: int = 0
    items: list[TransferItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    _status: SessionStatus = field(default=SessionStatus.PENDING)

    @property
    def status(self) -> SessionStatus:
        if self._status in (SessionStatus.EXPIRED, SessionStatus.CANCELLED):
            return self._status
        if not self.items:
            return self._status
        if all(i.status == ItemStatus.COMPLETED for i in self.items):
            return SessionStatus.READY
        if any(i.status in (ItemStatus.UPLOADING, ItemStatus.COMPLETED) for i in self.items):
            return SessionStatus.IN_PROGRESS
        return SessionStatus.PENDING

    @status.setter
    def status(self, val: SessionStatus) -> None:
        self._status = val

    @property
    def total_size_bytes(self) -> int:
        return sum(item.size_bytes for item in self.items)

    def add_item(self, item: TransferItem) -> None:
        self.items.append(item)
        self.updated_at = _utcnow()

    def record_download(self) -> None:
        self.download_count += 1
        self.updated_at = _utcnow()
        if self.burn_after_download:
            self._status = SessionStatus.EXPIRED

