import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_security_headers_present(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in resp.headers
    csp = resp.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
