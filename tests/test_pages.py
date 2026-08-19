import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_ui_pages_render(client: AsyncClient):
    routes = ["/", "/upload", "/download", "/files", "/s/7431-9285"]
    for route in routes:
        resp = await client.get(route)
        assert resp.status_code == 200
        assert "JUMBOX" in resp.text or "Jumbox" in resp.text
        assert "/static/app.css" in resp.text
        assert "/static/app.js" in resp.text

    # Verify upload has burn after download checkbox
    up_resp = await client.get("/upload")
    assert 'id="sessionBurnAfterDownload"' in up_resp.text

    # Verify download has burn warning banner element
    dl_resp = await client.get("/download")
    assert 'id="receiveBurnWarning"' in dl_resp.text

