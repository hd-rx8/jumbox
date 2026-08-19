from __future__ import annotations

from datetime import UTC, datetime, timedelta
import re
from pathlib import Path
from uuid import UUID, uuid4

from app.application.chunk_storage import ChunkStorage
from app.application.exceptions import (
    ItemNotFoundError,
    PermissionDeniedError,
    SessionExpiredError,
    SessionNotFoundError,
)
from app.application.transfer_codes import TransferCodeGenerator
from app.domain.auth import AuthenticatedUser
from app.domain.repositories import UnitOfWork
from app.domain.sessions import ItemStatus, SessionStatus, TransferItem, TransferSession
from app.domain.storage import FileStorage


def _sanitize_filename(name: str) -> str:
    cleaned = Path(name).name
    cleaned = re.sub(r'[^\w\-.]', '_', cleaned)
    return cleaned or "file"


def _is_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at < datetime.now(UTC)


class SessionService:
    def __init__(
        self,
        uow: UnitOfWork,
        storage: FileStorage,
        code_generator: TransferCodeGenerator | None = None,
        chunk_storage: ChunkStorage | None = None,
    ) -> None:
        self._uow = uow
        self._storage = storage
        self._code_generator = code_generator or TransferCodeGenerator()
        self._chunk_storage = chunk_storage

    async def create_session(
        self,
        owner: AuthenticatedUser,
        expires_in_seconds: int = 1800,
        burn_after_download: bool = False,
    ) -> TransferSession:
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds) if expires_in_seconds > 0 else None
        
        async with self._uow as uow:
            # Generate unique session code
            session_code = self._code_generator.generate_session_code()
            for _ in range(5):
                existing = await uow.sessions.get_by_code(session_code)
                if existing is None:
                    break
                session_code = self._code_generator.generate_session_code()

            session = TransferSession(
                owner_id=owner.user_id,
                session_code=session_code,
                expires_at=expires_at,
                burn_after_download=burn_after_download,
                _status=SessionStatus.PENDING,
            )
            await uow.sessions.add(session)
            await uow.commit()
            return session

    async def burn_session(self, session_id: UUID) -> None:
        async with self._uow as uow:
            session = await uow.sessions.get_by_id(session_id)
            if session is None:
                return
            session.record_download()
            session.status = SessionStatus.EXPIRED
            await uow.sessions.save(session)
            await uow.commit()
            
            for item in session.items:
                if item.storage_path:
                    try:
                        await self._storage.delete(item.stored_name or item.storage_path)
                    except Exception:
                        pass

    async def delete_session(self, session_id: UUID, owner: AuthenticatedUser) -> None:
        async with self._uow as uow:
            session = await uow.sessions.get_by_id(session_id)
            if session is None:
                raise SessionNotFoundError(f"Session {session_id} not found")
            if session.owner_id != owner.user_id and not owner.is_admin:
                raise PermissionDeniedError("Cannot delete a session you do not own")

            for item in session.items:
                if item.storage_path:
                    try:
                        await self._storage.delete(item.stored_name or item.storage_path)
                    except Exception:
                        pass
                if self._chunk_storage is not None:
                    try:
                        await self._chunk_storage.delete_part(session_id, item.id)
                    except Exception:
                        pass

            await uow.sessions.delete_by_id(session_id)
            await uow.commit()


    async def upload_item(
        self,
        session_id: UUID,
        owner: AuthenticatedUser,
        filename: str,
        file_content,
        size_bytes: int = 0,
    ) -> TransferItem:
        safe_filename = _sanitize_filename(filename)
        item_id = uuid4()
        dest_filename = f"{session_id}/{item_id}_{safe_filename}"

        async with self._uow as uow:
            session = await uow.sessions.get_by_id(session_id)
            if session is None:
                raise SessionNotFoundError(f"Session {session_id} not found")
            if session.owner_id != owner.user_id and not owner.is_admin:
                raise PermissionDeniedError("Cannot upload to a session you do not own")
            if _is_expired(session.expires_at):
                session.status = SessionStatus.EXPIRED
                await uow.sessions.save(session)
                await uow.commit()
                raise SessionExpiredError("Session has expired")

            item = TransferItem(
                id=item_id,
                session_id=session_id,
                original_name=filename,
                stored_name=f"{item_id}_{safe_filename}",
                size_bytes=size_bytes,
                status=ItemStatus.UPLOADING,
            )
            await uow.sessions.add_item(item)
            await uow.commit()

        try:
            stored_file = await self._storage.save_upload(
                source_name=filename,
                destination_name=dest_filename,
                content=file_content,
            )
            async with self._uow as uow:
                item = await uow.sessions.get_item_by_id(item_id)
                if item is None:
                    raise ItemNotFoundError(f"Item {item_id} not found")
                
                item.mark_completed(
                    checksum_sha256=stored_file.sha256,
                    storage_path=str(stored_file.path),
                    stored_name=f"{item_id}_{safe_filename}",
                )
                item.size_bytes = stored_file.size_bytes
                await uow.sessions.save_item(item)

                session = await uow.sessions.get_by_id(session_id)
                if session is not None:
                    # Trigger status update
                    _ = session.status
                    await uow.sessions.save(session)

                await uow.commit()
                return item
        except Exception as exc:
            async with self._uow as uow:
                item = await uow.sessions.get_item_by_id(item_id)
                if item is not None:
                    item.mark_failed(str(exc))
                    await uow.sessions.save_item(item)
                    await uow.commit()
            raise

    async def get_session_by_code(self, session_code: str) -> TransferSession | None:
        async with self._uow as uow:
            session = await uow.sessions.get_by_code(session_code)
            if session is None:
                return None
            if _is_expired(session.expires_at):
                session.status = SessionStatus.EXPIRED
                await uow.sessions.save(session)
                await uow.commit()
            return session

    async def get_session_by_id(self, session_id: UUID) -> TransferSession | None:
        async with self._uow as uow:
            return await uow.sessions.get_by_id(session_id)

    async def get_session_item(self, session_code: str, item_id: UUID) -> tuple[TransferSession, TransferItem] | None:
        async with self._uow as uow:
            session = await uow.sessions.get_by_code(session_code)
            if session is None:
                return None
            if _is_expired(session.expires_at) or session.status == SessionStatus.EXPIRED:
                session.status = SessionStatus.EXPIRED
                await uow.sessions.save(session)
                await uow.commit()
                return None
            
            for item in session.items:
                if item.id == item_id:
                    return session, item
            return None


    async def list_my_sessions(self, owner: AuthenticatedUser, limit: int = 50) -> list[TransferSession]:
        async with self._uow as uow:
            return list(await uow.sessions.list_for_owner(owner.user_id, limit=limit))

    async def init_resumable_item(
        self,
        *,
        session_id: UUID,
        owner: AuthenticatedUser,
        original_name: str,
        total_size_bytes: int,
        expected_sha256: str | None = None,
    ) -> TransferItem:
        safe_filename = _sanitize_filename(original_name)
        item_id = uuid4()

        async with self._uow as uow:
            session = await uow.sessions.get_by_id(session_id)
            if session is None:
                raise SessionNotFoundError(f"Session {session_id} not found")
            if session.owner_id != owner.user_id and not owner.is_admin:
                raise PermissionDeniedError("Cannot upload to a session you do not own")
            if _is_expired(session.expires_at):
                session.status = SessionStatus.EXPIRED
                await uow.sessions.save(session)
                await uow.commit()
                raise SessionExpiredError("Session has expired")

            item = TransferItem(
                id=item_id,
                session_id=session_id,
                original_name=original_name,
                stored_name=f"{item_id}_{safe_filename}",
                size_bytes=total_size_bytes,
                checksum_sha256=expected_sha256,
                status=ItemStatus.QUEUED,
            )
            await uow.sessions.add_item(item)
            await uow.commit()
            return item

    async def get_item_offset(self, session_id: UUID, item_id: UUID) -> tuple[TransferItem, int]:
        if self._chunk_storage is None:
            raise RuntimeError("ChunkStorage is not configured")

        async with self._uow as uow:
            session = await uow.sessions.get_by_id(session_id)
            if session is None:
                raise SessionNotFoundError(f"Session {session_id} not found")
            item = await uow.sessions.get_item_by_id(item_id)
            if item is None or item.session_id != session_id:
                raise ItemNotFoundError(f"Item {item_id} not found")

        offset = await self._chunk_storage.get_offset(session_id, item_id)
        return item, offset

    async def append_item_chunk(
        self,
        *,
        session_id: UUID,
        item_id: UUID,
        owner: AuthenticatedUser,
        chunk_data: bytes,
        offset: int,
    ) -> tuple[TransferItem, int, bool]:
        if self._chunk_storage is None:
            raise RuntimeError("ChunkStorage is not configured")

        async with self._uow as uow:
            session = await uow.sessions.get_by_id(session_id)
            if session is None:
                raise SessionNotFoundError(f"Session {session_id} not found")
            if session.owner_id != owner.user_id and not owner.is_admin:
                raise PermissionDeniedError("Cannot upload to a session you do not own")
            if _is_expired(session.expires_at):
                session.status = SessionStatus.EXPIRED
                await uow.sessions.save(session)
                await uow.commit()
                raise SessionExpiredError("Session has expired")

            item = await uow.sessions.get_item_by_id(item_id)
            if item is None or item.session_id != session_id:
                raise ItemNotFoundError(f"Item {item_id} not found")

        # Append to storage
        new_offset = await self._chunk_storage.append_chunk(session_id, item_id, chunk_data, offset)

        if new_offset >= item.size_bytes and item.size_bytes > 0:
            # Finalize
            safe_name = _sanitize_filename(item.original_name)
            computed_sha, dest_path, final_size = await self._chunk_storage.finalize_chunk_upload(
                session_id=session_id,
                item_id=item_id,
                safe_filename=safe_name,
                expected_sha256=item.checksum_sha256,
            )
            async with self._uow as uow:
                item = await uow.sessions.get_item_by_id(item_id)
                if item is not None:
                    item.mark_completed(
                        checksum_sha256=computed_sha,
                        storage_path=str(dest_path),
                        stored_name=f"{item_id}_{safe_name}",
                    )
                    item.size_bytes = final_size
                    await uow.sessions.save_item(item)

                session = await uow.sessions.get_by_id(session_id)
                if session is not None:
                    _ = session.status
                    await uow.sessions.save(session)

                await uow.commit()
                return item, new_offset, True
        else:
            async with self._uow as uow:
                item = await uow.sessions.get_item_by_id(item_id)
                if item is not None:
                    item.mark_uploading()
                    await uow.sessions.save_item(item)
                await uow.commit()
            return item, new_offset, False

