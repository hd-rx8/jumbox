import asyncio
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.settings import Settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import get_session_factory
from app.application.uow import SQLAlchemyUnitOfWork
from app.application.security import HMACTokenService, PBKDF2PasswordHasher, build_jwt_secret
from app.domain.auth import AuthenticatedUser
from app.main import create_app


@pytest.mark.anyio
async def test_standalone_mode_without_redis(tmp_path: Path):
    db_path = tmp_path / "standalone.db"
    settings = Settings(
        app_name="Jumbox Standalone",
        environment="test",
        data_dir=tmp_path,
        uploads_dir=tmp_path / "uploads",
        temp_dir=tmp_path / "tmp",
        database_url=f"sqlite+aiosqlite:///{db_path}",
        redis_url="",  # No Redis in standalone mode
        cleanup_interval_seconds=1,
    )

    # 1. DB schema migration / creation
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    # 2. UoW without Redis
    factory = get_session_factory(settings.database_url)
    uow = SQLAlchemyUnitOfWork(factory, redis_url="")
    async with uow:
        assert uow.session is not None
        assert uow.redis is None

    # 3. Create standalone app and test lifespan + API calls without Redis
    app = create_app(settings)
    
    from uuid import uuid4
    # Generate auth header
    user = AuthenticatedUser(user_id=uuid4(), email="standalone@jumbox.local")
    secret = build_jwt_secret(f"{settings.app_name}:{settings.database_url}:{settings.redis_url}")
    token = HMACTokenService(secret_key=secret, issuer=settings.app_name).create_access_token(user)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Health check
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Register user in standalone mode
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "newuser@jumbox.local", "password": "password123", "display_name": "New User"},
        )
        assert reg_resp.status_code == 201
        reg_data = reg_resp.json()
        assert "access_token" in reg_data
        user_token = reg_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {user_token}"}

        # Login with registered user
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "newuser@jumbox.local", "password": "password123"},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

        # Create session with the registered user's token
        resp = await client.post("/api/v1/sessions", json={"expires_in_seconds": 600}, headers=auth_headers)
        assert resp.status_code == 201
        session_data = resp.json()
        assert session_data["session_code"] is not None

        # Upload file in standalone mode
        session_id = session_data["session_id"]
        files = {"file": ("test.txt", b"standalone file content", "text/plain")}
        up_resp = await client.post(f"/api/v1/sessions/{session_id}/items", files=files, headers=auth_headers)
        assert up_resp.status_code == 201
        item_id = up_resp.json()["item_id"]

        # Download file
        code = session_data["session_code"]
        dl_resp = await client.get(f"/api/v1/sessions/{code}/items/{item_id}/download")
        assert dl_resp.status_code == 200
        assert dl_resp.content == b"standalone file content"

    # Allow lifespan cleanup task to cancel cleanly
    await asyncio.sleep(0.1)


@pytest.mark.anyio
async def test_standalone_zero_config_auto_migration(tmp_path: Path):
    db_path = tmp_path / "fresh_zero_config.db"
    settings = Settings(
        app_name="Jumbox Standalone Auto",
        environment="test",
        data_dir=tmp_path,
        uploads_dir=tmp_path / "uploads",
        temp_dir=tmp_path / "tmp",
        database_url=f"sqlite+aiosqlite:///{db_path}",
        redis_url="",
        cleanup_interval_seconds=1,
    )

    # Directly create app WITHOUT manual Base.metadata.create_all
    app = create_app(settings)

    # Lifespan will trigger Base.metadata.create_all on startup
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Register a brand new user on the zero-config database
            reg_resp = await client.post(
                "/api/v1/auth/register",
                json={"email": "fresh@jumbox.local", "password": "securepassword123"},
            )
            assert reg_resp.status_code == 201
            data = reg_resp.json()
            assert "access_token" in data

