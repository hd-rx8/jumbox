from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.auth_service import AuthService
from app.application.exceptions import AuthenticationError
from app.application.security import HMACTokenService, PBKDF2PasswordHasher, build_jwt_secret
from app.application.sessions_service import SessionService
from app.application.transfer_codes import TransferCodeGenerator
from app.application.uow import SQLAlchemyUnitOfWork
from app.core.settings import Settings, get_settings as get_global_settings
from app.domain.auth import AuthenticatedUser
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.storage.local import LocalFileStorage

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    if hasattr(request.app.state, "settings") and request.app.state.settings is not None:
        return request.app.state.settings
    return get_global_settings()


def get_uow(settings: Settings = Depends(get_settings)) -> SQLAlchemyUnitOfWork:
    return SQLAlchemyUnitOfWork(get_session_factory(settings.database_url), settings.redis_url)


def get_password_hasher() -> PBKDF2PasswordHasher:
    return PBKDF2PasswordHasher()


def get_token_service(settings: Settings = Depends(get_settings)) -> HMACTokenService:
    secret = build_jwt_secret(f"{settings.app_name}:{settings.database_url}:{settings.redis_url}")
    return HMACTokenService(secret_key=secret, issuer=settings.app_name)


def get_auth_service(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    password_hasher: PBKDF2PasswordHasher = Depends(get_password_hasher),
    token_service: HMACTokenService = Depends(get_token_service),
) -> AuthService:
    return AuthService(uow=uow, password_hasher=password_hasher, token_service=token_service)


from app.application.chunk_storage import ChunkStorage


def get_session_service(
    settings: Settings = Depends(get_settings),
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> SessionService:
    storage = LocalFileStorage(settings.uploads_dir)
    chunk_storage = ChunkStorage(temp_root=settings.temp_dir, uploads_root=settings.uploads_dir)
    return SessionService(
        uow=uow,
        storage=storage,
        code_generator=TransferCodeGenerator(),
        chunk_storage=chunk_storage,
    )


def get_current_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return credentials.credentials


def get_current_user(
    token: str = Depends(get_current_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthenticatedUser:
    try:
        return auth_service.get_current_user(token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
