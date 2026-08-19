from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.api.router import api_router
from app.api.routes.pages import ui_router
from app.application.cleanup_service import CleanupService
from app.application.uow import SQLAlchemyUnitOfWork
from app.core.logging import configure_logging
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.settings import Settings, get_settings
from app.infrastructure.db.base import Base
import app.infrastructure.db.models  # noqa: F401
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.security.rate_limiter import RateLimiterMiddleware
from app.infrastructure.storage.local import LocalFileStorage


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        resolved_settings.ensure_storage_directories()

        # Automatically create tables for SQLite/standalone mode
        if "sqlite" in resolved_settings.database_url:
            init_engine = create_async_engine(resolved_settings.database_url, echo=False)
            async with init_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            await init_engine.dispose()

        cleanup_task: asyncio.Task | None = None
        if not resolved_settings.redis_url or "sqlite" in resolved_settings.database_url:
            async def _periodic_cleanup() -> None:
                session_factory = get_session_factory(resolved_settings.database_url)
                file_storage = LocalFileStorage(resolved_settings.uploads_dir)
                while True:
                    try:
                        await asyncio.sleep(resolved_settings.cleanup_interval_seconds)
                        uow = SQLAlchemyUnitOfWork(session_factory, resolved_settings.redis_url)
                        service = CleanupService(
                            uow=uow,
                            file_storage=file_storage,
                            temp_dir=resolved_settings.temp_dir,
                        )
                        await service.cleanup_all()
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        pass

            cleanup_task = asyncio.create_task(_periodic_cleanup())
        try:
            yield
        finally:
            if cleanup_task is not None:
                cleanup_task.cancel()
                try:
                    await cleanup_task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimiterMiddleware)
    static_root = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_root), name="static")
    app.include_router(ui_router)
    app.include_router(api_router, prefix=resolved_settings.api_prefix)
    return app


app = create_app()
