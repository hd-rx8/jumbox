import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_session_lifecycle_api(client: AsyncClient, auth_headers: dict):
    # 1. Create session
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"expires_in_seconds": 1800},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    session_data = create_resp.json()
    session_id = session_data["session_id"]
    code = session_data["session_code"]
    assert code is not None
    assert "-" in code

    # 2. Upload items
    files = {"file": ("document.pdf", b"%PDF-1.4 sample pdf content", "application/pdf")}
    upload_resp = await client.post(
        f"/api/v1/sessions/{session_id}/items",
        files=files,
        headers=auth_headers,
    )
    assert upload_resp.status_code == 201, upload_resp.text
    item_data = upload_resp.json()
    item_id = item_data["item_id"]
    assert item_data["original_name"] == "document.pdf"
    assert item_data["status"] == "completed"
    assert item_data["checksum_sha256"] is not None

    # Upload second item
    files2 = {"file": ("image.png", b"\x89PNG\r\n\x1a\nsample png content", "image/png")}
    upload_resp2 = await client.post(
        f"/api/v1/sessions/{session_id}/items",
        files=files2,
        headers=auth_headers,
    )
    assert upload_resp2.status_code == 201
    item2_data = upload_resp2.json()
    item2_id = item2_data["item_id"]

    # 3. Get session metadata (public via session_code)
    meta_resp = await client.get(f"/api/v1/sessions/{code}")
    assert meta_resp.status_code == 200, meta_resp.text
    meta_data = meta_resp.json()
    assert meta_data["session_code"] == code
    assert len(meta_data["items"]) == 2
    assert meta_data["total_size_bytes"] > 0
    assert meta_data["status"] == "ready"

    # 4. Download item
    dl_resp = await client.get(f"/api/v1/sessions/{code}/items/{item_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.content == b"%PDF-1.4 sample pdf content"
    assert "content-disposition" in dl_resp.headers
    assert dl_resp.headers.get("x-checksum-sha256") == item_data["checksum_sha256"]
    assert dl_resp.headers.get("accept-ranges") == "bytes"

    # 5. QR Code endpoint
    qr_resp = await client.get(f"/api/v1/sessions/{code}/qr.png")
    assert qr_resp.status_code == 200
    assert qr_resp.headers["content-type"] == "image/png"

    # 6. List my sessions
    mine_resp = await client.get("/api/v1/sessions/mine", headers=auth_headers)
    assert mine_resp.status_code == 200
    mine_data = mine_resp.json()
    assert isinstance(mine_data, list)
    assert any(s["session_id"] == session_id for s in mine_data)

@pytest.mark.anyio
async def test_get_nonexistent_session(client: AsyncClient):
    resp = await client.get("/api/v1/sessions/0000-0000")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_burn_after_download_session(client: AsyncClient, auth_headers: dict):
    # 1. Create ephemeral session
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"expires_in_seconds": 1800, "burn_after_download": True},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    session_id = data["session_id"]
    code = data["session_code"]
    assert data["burn_after_download"] is True

    # 2. Upload item
    files = {"file": ("secret.txt", b"confidential content", "text/plain")}
    up_resp = await client.post(f"/api/v1/sessions/{session_id}/items", files=files, headers=auth_headers)
    assert up_resp.status_code == 201
    item_id = up_resp.json()["item_id"]

    # 3. First download succeeds
    dl_resp = await client.get(f"/api/v1/sessions/{code}/items/{item_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.content == b"confidential content"

    # 4. Subsequent metadata request shows expired or 410 / download returns 410 GONE
    dl2_resp = await client.get(f"/api/v1/sessions/{code}/items/{item_id}/download")
    assert dl2_resp.status_code in (404, 410)

    # Subsequent metadata request indicates expired
    meta_resp = await client.get(f"/api/v1/sessions/{code}")
    assert meta_resp.status_code == 200
    assert meta_resp.json()["status"] == "expired"


@pytest.mark.anyio
async def test_delete_session_api(client: AsyncClient, auth_headers: dict):
    # 1. Create session
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"expires_in_seconds": 1800},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    session_id = data["session_id"]
    code = data["session_code"]

    # 2. Upload item
    files = {"file": ("manual_delete.txt", b"delete me early", "text/plain")}
    up_resp = await client.post(f"/api/v1/sessions/{session_id}/items", files=files, headers=auth_headers)
    assert up_resp.status_code == 201

    # 3. Delete session via API
    del_resp = await client.delete(f"/api/v1/sessions/{session_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # 4. Lookup returns 404
    get_resp = await client.get(f"/api/v1/sessions/{code}")
    assert get_resp.status_code == 404


