import hashlib
from pathlib import Path
from uuid import UUID
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_resumable_upload_lifecycle(client: AsyncClient, auth_headers: dict):
    # 1. Create a session
    resp = await client.post("/api/v1/sessions", json={"expires_in_seconds": 1800}, headers=auth_headers)
    assert resp.status_code == 201
    session_data = resp.json()
    session_id = session_data["session_id"]
    session_code = session_data["session_code"]

    payload = b"Hello, this is chunk 1. " + b"And here is chunk 2 with more data!"
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    total_size = len(payload)
    chunk1 = payload[:20]
    chunk2 = payload[20:]

    # 2. Initialize resumable item
    init_resp = await client.post(
        f"/api/v1/sessions/{session_id}/items/resumable",
        json={
            "original_name": "test_resumable.txt",
            "total_size_bytes": total_size,
            "expected_sha256": expected_sha256,
        },
        headers=auth_headers,
    )
    assert init_resp.status_code == 201
    item_data = init_resp.json()
    item_id = item_data["item_id"]
    assert item_data["status"] in ("queued", "uploading")

    # 3. Probe offset before uploading
    offset_resp = await client.get(f"/api/v1/sessions/{session_id}/items/{item_id}/offset")
    assert offset_resp.status_code == 200
    assert offset_resp.json()["bytes_received"] == 0
    assert offset_resp.headers.get("Upload-Offset") == "0"

    # 4. Upload chunk 1 (20 bytes) at offset 0
    chunk1_resp = await client.patch(
        f"/api/v1/sessions/{session_id}/items/{item_id}/chunks",
        content=chunk1,
        headers={**auth_headers, "Upload-Offset": "0", "Content-Type": "application/octet-stream"},
    )
    assert chunk1_resp.status_code == 200
    assert chunk1_resp.json()["bytes_received"] == 20
    assert chunk1_resp.json()["completed"] is False

    # 5. Probe offset after chunk 1
    offset_resp2 = await client.get(f"/api/v1/sessions/{session_id}/items/{item_id}/offset")
    assert offset_resp2.status_code == 200
    assert offset_resp2.json()["bytes_received"] == 20
    assert offset_resp2.headers.get("Upload-Offset") == "20"

    # 6. Out-of-order / duplicate chunk sends wrong offset -> Conflict 409
    bad_offset_resp = await client.patch(
        f"/api/v1/sessions/{session_id}/items/{item_id}/chunks",
        content=chunk2,
        headers={**auth_headers, "Upload-Offset": "0", "Content-Type": "application/octet-stream"},
    )
    assert bad_offset_resp.status_code == 409
    assert bad_offset_resp.headers.get("Upload-Offset") == "20"

    # 7. Upload chunk 2 (remaining bytes) at offset 20 -> Finalizes upload
    chunk2_resp = await client.patch(
        f"/api/v1/sessions/{session_id}/items/{item_id}/chunks",
        content=chunk2,
        headers={**auth_headers, "Upload-Offset": "20", "Content-Type": "application/octet-stream"},
    )
    assert chunk2_resp.status_code == 200
    assert chunk2_resp.json()["bytes_received"] == total_size
    assert chunk2_resp.json()["completed"] is True
    assert chunk2_resp.json()["checksum_sha256"] == expected_sha256

    # 8. Download and verify assembled content
    dl_resp = await client.get(f"/api/v1/sessions/{session_code}/items/{item_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.content == payload


@pytest.mark.anyio
async def test_resumable_checksum_mismatch(client: AsyncClient, auth_headers: dict):
    # 1. Create a session
    resp = await client.post("/api/v1/sessions", json={"expires_in_seconds": 1800}, headers=auth_headers)
    assert resp.status_code == 201
    session_id = resp.json()["session_id"]

    # 2. Init with mismatched expected sha256
    init_resp = await client.post(
        f"/api/v1/sessions/{session_id}/items/resumable",
        json={
            "original_name": "corrupt.txt",
            "total_size_bytes": 10,
            "expected_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        },
        headers=auth_headers,
    )
    assert init_resp.status_code == 201
    item_id = init_resp.json()["item_id"]

    # 3. Upload full 10 bytes
    chunk_resp = await client.patch(
        f"/api/v1/sessions/{session_id}/items/{item_id}/chunks",
        content=b"0123456789",
        headers={**auth_headers, "Upload-Offset": "0", "Content-Type": "application/octet-stream"},
    )
    assert chunk_resp.status_code == 400
    assert "checksum" in chunk_resp.json()["detail"].lower()
