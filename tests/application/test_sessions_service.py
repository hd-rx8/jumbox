import io
import pytest
from uuid import uuid4
from datetime import UTC, datetime, timedelta
from app.application.exceptions import PermissionDeniedError, SessionExpiredError, SessionNotFoundError
from app.application.sessions_service import SessionService
from app.domain.auth import AuthenticatedUser
from app.domain.sessions import TransferSession, TransferItem, SessionStatus, ItemStatus
from app.domain.storage import StoredFile

class FakeSessionRepository:
    def __init__(self):
        self.sessions = {}
        self.items = {}

    async def add(self, session: TransferSession) -> TransferSession:
        self.sessions[session.id] = session
        return session

    async def save(self, session: TransferSession) -> TransferSession:
        self.sessions[session.id] = session
        return session

    async def delete_by_id(self, session_id):
        self.sessions.pop(session_id, None)

    async def get_by_id(self, session_id):
        session = self.sessions.get(session_id)
        if session:
            session.items = [i for i in self.items.values() if i.session_id == session_id]
        return session

    async def get_by_code(self, session_code: str):
        normalized = session_code.replace(" ", "").strip().lower()
        for s in self.sessions.values():
            if s.session_code.replace("-", "").lower() == normalized.replace("-", "") or s.session_code.lower() == normalized:
                s.items = [i for i in self.items.values() if i.session_id == s.id]
                return s
        return None

    async def list_for_owner(self, owner_id, limit=50):
        res = [s for s in self.sessions.values() if s.owner_id == owner_id]
        for s in res:
            s.items = [i for i in self.items.values() if i.session_id == s.id]
        return res[:limit]

    async def add_item(self, item: TransferItem) -> TransferItem:
        self.items[item.id] = item
        if item.session_id in self.sessions:
            self.sessions[item.session_id].items = [i for i in self.items.values() if i.session_id == item.session_id]
        return item

    async def save_item(self, item: TransferItem) -> TransferItem:
        self.items[item.id] = item
        return item

    async def get_item_by_id(self, item_id):
        return self.items.get(item_id)

    async def list_expired_before(self, deadline: datetime):
        return [s for s in self.sessions.values() if s.expires_at and s.expires_at <= deadline]

    async def expire_before(self, deadline: datetime) -> int:
        count = 0
        for s in self.sessions.values():
            if s.expires_at and s.expires_at <= deadline:
                s.status = SessionStatus.EXPIRED
                count += 1
        return count


class FakeUnitOfWork:
    def __init__(self):
        self.sessions = FakeSessionRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.rolled_back = True

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class FakeStorage:
    def __init__(self, tmp_path):
        self.root = tmp_path

    async def save_upload(self, *, source_name: str, destination_name: str, content):
        import hashlib
        dest = self.root / destination_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        sha = hashlib.sha256()
        
        if hasattr(content, 'read'):
            data = content.read()
        elif hasattr(content, 'file'):
            data = content.file.read()
        elif isinstance(content, bytes):
            data = content
        else:
            data = str(content).encode()
            
        dest.write_bytes(data)
        sha.update(data)
        return StoredFile(path=dest, size_bytes=len(data), sha256=sha.hexdigest())

    async def delete(self, stored_file: StoredFile):
        if stored_file.path.exists():
            stored_file.path.unlink()


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.file = io.BytesIO(content)
        self.size = len(content)


@pytest.mark.anyio
async def test_create_session_and_upload_item(tmp_path):
    uow = FakeUnitOfWork()
    storage = FakeStorage(tmp_path)
    service = SessionService(uow=uow, storage=storage)
    user = AuthenticatedUser(user_id=uuid4(), email='user@jumbox.local', is_admin=False)
    
    session_result = await service.create_session(owner=user, expires_in_seconds=1800)
    assert session_result.session_code is not None
    assert len(session_result.session_code) == 9  # format: 'XXXX-XXXX'
    
    upload = FakeUploadFile('test_file.txt', b'Hello Jumbox')
    item_result = await service.upload_item(
        session_id=session_result.id,
        owner=user,
        filename='test_file.txt',
        file_content=upload,
    )
    assert item_result.status == ItemStatus.COMPLETED
    assert item_result.checksum_sha256 is not None
    assert item_result.size_bytes == 12

    # Get by code
    fetched_session = await service.get_session_by_code(session_result.session_code)
    assert fetched_session is not None
    assert len(fetched_session.items) == 1
    assert fetched_session.status == SessionStatus.READY

    # Get session item
    res = await service.get_session_item(session_result.session_code, item_result.id)
    assert res is not None
    _, item = res
    assert item.id == item_result.id


@pytest.mark.anyio
async def test_upload_item_permission_denied(tmp_path):
    uow = FakeUnitOfWork()
    storage = FakeStorage(tmp_path)
    service = SessionService(uow=uow, storage=storage)
    owner = AuthenticatedUser(user_id=uuid4(), email='owner@jumbox.local', is_admin=False)
    stranger = AuthenticatedUser(user_id=uuid4(), email='other@jumbox.local', is_admin=False)
    
    session = await service.create_session(owner=owner, expires_in_seconds=1800)
    
    upload = FakeUploadFile('evil.txt', b'hacked')
    with pytest.raises(PermissionDeniedError):
        await service.upload_item(
            session_id=session.id,
            owner=stranger,
            filename='evil.txt',
            file_content=upload,
        )
