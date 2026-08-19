import pytest
from httpx import ASGITransport, AsyncClient
from app.api.dependencies import get_current_user


@pytest.mark.anyio
async def test_auth_me_requires_valid_bearer_token(app):
    # Remove mock override for get_current_user to test real auth dependency
    app.dependency_overrides.pop(get_current_user, None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing header
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

        # Invalid token
        resp_invalid = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert resp_invalid.status_code == 401
