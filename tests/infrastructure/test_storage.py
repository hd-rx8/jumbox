import io
import pytest
from pathlib import Path
from app.domain.storage import StoredFile
from app.infrastructure.storage.local import LocalFileStorage

class DummyUpload:
    def __init__(self, data: bytes):
        self.file = io.BytesIO(data)

@pytest.mark.anyio
async def test_local_storage_save_and_delete(tmp_path: Path):
    storage = LocalFileStorage(tmp_path)
    data = b"Streaming and integrity test content" * 1024
    
    upload = DummyUpload(data)
    stored = await storage.save_upload(
        source_name="data.bin",
        destination_name="subfolder/item1_data.bin",
        content=upload,
    )
    
    assert stored.path.exists()
    assert stored.size_bytes == len(data)
    assert len(stored.sha256) == 64
    
    # Verify file content
    assert stored.path.read_bytes() == data
    
    # Delete
    await storage.delete(stored)
    assert not stored.path.exists()
