import asyncio
from pathlib import Path
import tempfile
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from uuid import uuid4

from app.main import create_app
from app.core.settings import Settings, get_settings
from app.domain.auth import AuthenticatedUser
from app.application.security import HMACTokenService, PBKDF2PasswordHasher, build_jwt_secret
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import get_engine, get_session_factory
from app.api.dependencies import get_current_user, get_settings as dep_get_settings, get_uow
from app.application.uow import SQLAlchemyUnitOfWork

@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        (path / "uploads").mkdir(parents=True, exist_ok=True)
        (path / "tmp").mkdir(parents=True, exist_ok=True)
        yield path

@pytest.fixture
def test_db_path(temp_data_dir):
    return temp_data_dir / "test.db"

@pytest.fixture
def test_settings(temp_data_dir, test_db_path):
    return Settings(
        app_name="Jumbox Test",
        environment="test",
        data_dir=temp_data_dir,
        uploads_dir=temp_data_dir / "uploads",
        temp_dir=temp_data_dir / "tmp",
        database_url=f"sqlite+aiosqlite:///{test_db_path}",
    )

@pytest.fixture
def auth_user():
    return AuthenticatedUser(user_id=uuid4(), email="tester@jumbox.local", is_admin=False)

@pytest.fixture
def auth_headers(test_settings, auth_user):
    secret = build_jwt_secret(f"{test_settings.app_name}:{test_settings.database_url}:{test_settings.redis_url}")
    token_service = HMACTokenService(secret_key=secret, issuer=test_settings.app_name)
    token = token_service.create_access_token(auth_user)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def app(test_settings, auth_user):
    # Setup SQLite schema
    engine = create_async_engine(test_settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    
    application = create_app(test_settings)
    
    def override_get_uow():
        return SQLAlchemyUnitOfWork(session_factory, test_settings.redis_url)
        
    def override_get_settings():
        return test_settings
        
    def override_get_current_user():
        return auth_user

    application.dependency_overrides[get_uow] = override_get_uow
    application.dependency_overrides[dep_get_settings] = override_get_settings
    application.dependency_overrides[get_current_user] = override_get_current_user
    
    yield application
    await engine.dispose()

@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
