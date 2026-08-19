from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import time

from app.domain.repositories import UnitOfWork
from app.domain.storage import FileStorage, StoredFile


class CleanupService:
    def __init__(
        self,
        uow: UnitOfWork,
        file_storage: FileStorage,
        temp_dir: Path | None = None,
    ) -> None:
        self._uow = uow
        self._file_storage = file_storage
        self._temp_dir = temp_dir

    async def cleanup_expired_transfers(self, *, deadline: datetime | None = None) -> int:
        cutoff = deadline or datetime.now(UTC)
        async with self._uow as uow:
            expired_transfers = await uow.transfers.list_expired_before(cutoff)
            removed = 0
            for transfer in expired_transfers:
                if transfer.storage_path:
                    await self._file_storage.delete(
                        StoredFile(
                            path=Path(transfer.storage_path),
                            size_bytes=transfer.size_bytes,
                            sha256=transfer.checksum_sha256 or "",
                        )
                    )
                await uow.transfers.delete_by_id(transfer.id)
                removed += 1

            await uow.commit()
            return removed

    async def cleanup_expired_sessions(self, *, deadline: datetime | None = None) -> int:
        cutoff = deadline or datetime.now(UTC)
        async with self._uow as uow:
            expired_sessions = await uow.sessions.list_expired_before(cutoff)
            removed = 0
            for session in expired_sessions:
                for item in session.items:
                    if item.storage_path:
                        await self._file_storage.delete(
                            StoredFile(
                                path=Path(item.storage_path),
                                size_bytes=item.size_bytes,
                                sha256=item.checksum_sha256 or "",
                            )
                        )
                await uow.sessions.delete_by_id(session.id)
                removed += 1

            await uow.commit()
            return removed

    async def cleanup_orphaned_temp_files(self, *, max_age_seconds: int = 3600) -> int:
        if self._temp_dir is None or not self._temp_dir.exists():
            return 0

        now = time.time()
        removed = 0
        for entry in self._temp_dir.iterdir():
            if entry.is_file():
                try:
                    file_mtime = entry.stat().st_mtime
                    if now - file_mtime >= max_age_seconds:
                        entry.unlink(missing_ok=True)
                        removed += 1
                except OSError:
                    continue
        return removed

    async def cleanup_all(self) -> dict[str, int]:
        sessions_removed = await self.cleanup_expired_sessions()
        transfers_removed = await self.cleanup_expired_transfers()
        temp_files_removed = await self.cleanup_orphaned_temp_files()
        return {
            'sessions': sessions_removed,
            'transfers': transfers_removed,
            'temp_files': temp_files_removed,
        }
