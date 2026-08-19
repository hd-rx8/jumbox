from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
from uuid import UUID
import anyio


class ChunkStorage:
    def __init__(self, temp_root: Path, uploads_root: Path) -> None:
        self._temp_root = temp_root
        self._uploads_root = uploads_root
        self._temp_root.mkdir(parents=True, exist_ok=True)
        self._uploads_root.mkdir(parents=True, exist_ok=True)

    def _part_path(self, session_id: UUID, item_id: UUID) -> Path:
        return self._temp_root / str(session_id) / f"{item_id}.part"

    async def get_offset(self, session_id: UUID, item_id: UUID) -> int:
        part_path = self._part_path(session_id, item_id)
        if not part_path.exists():
            return 0
        stat = await anyio.Path(part_path).stat()
        return stat.st_size

    async def append_chunk(self, session_id: UUID, item_id: UUID, data: bytes, offset: int) -> int:
        part_path = self._part_path(session_id, item_id)
        part_path.parent.mkdir(parents=True, exist_ok=True)

        current_size = part_path.stat().st_size if part_path.exists() else 0
        if current_size != offset:
            raise ValueError(f"Offset mismatch: expected {current_size}, got {offset}")

        def _write() -> None:
            with part_path.open("ab") as f:
                f.write(data)

        await anyio.to_thread.run_sync(_write)
        return current_size + len(data)

    async def finalize_chunk_upload(
        self,
        session_id: UUID,
        item_id: UUID,
        safe_filename: str,
        expected_sha256: str | None = None,
    ) -> tuple[str, Path, int]:
        part_path = self._part_path(session_id, item_id)
        if not part_path.exists():
            raise FileNotFoundError("Part file not found")

        def _calc_hash() -> tuple[str, int]:
            sha = hashlib.sha256()
            with part_path.open("rb") as f:
                while chunk := f.read(1024 * 1024):
                    sha.update(chunk)
            return sha.hexdigest(), part_path.stat().st_size

        computed_hash, size_bytes = await anyio.to_thread.run_sync(_calc_hash)

        if expected_sha256 and computed_hash.lower() != expected_sha256.lower():
            raise ValueError(f"Checksum mismatch: expected {expected_sha256}, got {computed_hash}")

        dest_dir = self._uploads_root / str(session_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{item_id}_{safe_filename}"

        await anyio.to_thread.run_sync(shutil.move, str(part_path), str(dest_path))
        return computed_hash, dest_path, size_bytes

    async def delete_part(self, session_id: UUID, item_id: UUID) -> None:
        part_path = self._part_path(session_id, item_id)
        if part_path.exists():
            await anyio.Path(part_path).unlink(missing_ok=True)
