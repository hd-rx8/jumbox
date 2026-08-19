import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_auth_login_rate_limiting(client: AsyncClient):
    # Attempt 10 failed login requests (within limit)
    for _ in range(10):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "wrongpassword"}
        )
        assert resp.status_code in (401, 422)

    # 11th request exceeds limit and must return 429
    resp_blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@test.com", "password": "wrongpassword"}
    )
    assert resp_blocked.status_code == 429
    assert "Retry-After" in resp_blocked.headers
    data = resp_blocked.json()
    assert "detail" in data
