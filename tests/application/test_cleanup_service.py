import pytest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.application.cleanup_service import CleanupService
from app.domain.sessions import SessionStatus, TransferItem, TransferSession
from app.domain.storage import StoredFile


class FakeCleanupSessionRepo:
    def __init__(self):
        self.sessions = {}
        self.items = {}

    async def list_expired_before(self, deadline: datetime):
        return [
            s for s in self.sessions.values()
            if s.expires_at and (s.expires_at.replace(tzinfo=UTC) if s.expires_at.tzinfo is None else s.expires_at) <= deadline
        ]

    async def delete_by_id(self, session_id):
        self.sessions.pop(session_id, None)
        self.items = {k: v for k, v in self.items.items() if v.session_id != session_id}


class FakeCleanupTransferRepo:
    def __init__(self):
        self.transfers = {}

    async def list_expired_before(self, deadline: datetime):
        return [
            t for t in self.transfers.values()
            if t.expires_at and (t.expires_at.replace(tzinfo=UTC) if t.expires_at.tzinfo is None else t.expires_at) <= deadline
        ]

    async def delete_by_id(self, transfer_id):
        self.transfers.pop(transfer_id, None)


class FakeCleanupUoW:
    def __init__(self):
        self.sessions = FakeCleanupSessionRepo()
        self.transfers = FakeCleanupTransferRepo()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def commit(self):
        pass


class FakeCleanupStorage:
    def __init__(self):
        self.deleted_files = []

    async def delete(self, stored_file: StoredFile):
        self.deleted_files.append(stored_file.path)
        if stored_file.path.exists():
            stored_file.path.unlink()


@pytest.mark.anyio
async def test_cleanup_expired_sessions_and_temp_files(tmp_path: Path):
    uow = FakeCleanupUoW()
    storage = FakeCleanupStorage()
    temp_dir = tmp_path / 'tmp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Create orphaned temp file
    orphan_file = temp_dir / 'orphaned.part'
    orphan_file.write_bytes(b'temporary chunk data')
    
    # Create expired session with an item file
    file_path = tmp_path / 'uploads' / 'session1' / 'doc.pdf'
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b'content')
    
    session = TransferSession(
        owner_id=uuid4(),
        session_code='1111-2222',
        expires_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    item = TransferItem(
        session_id=session.id,
        original_name='doc.pdf',
        size_bytes=7,
        storage_path=str(file_path),
        checksum_sha256='dummy',
    )
    session.items.append(item)
    uow.sessions.sessions[session.id] = session
    uow.sessions.items[item.id] = item
    
    service = CleanupService(uow=uow, file_storage=storage, temp_dir=temp_dir)
    
    cleaned_sessions = await service.cleanup_expired_sessions()
    assert cleaned_sessions == 1
    assert not file_path.exists()
    assert session.id not in uow.sessions.sessions
    
    cleaned_temp = await service.cleanup_orphaned_temp_files(max_age_seconds=0)
    assert cleaned_temp == 1
    assert not orphan_file.exists()
