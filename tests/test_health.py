import pytest
from httpx import ASGITransport, AsyncClient
from app.main import create_app
from app.core.settings import Settings

@pytest.mark.anyio
async def test_health_endpoint():
    app = create_app(Settings(environment="test"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
