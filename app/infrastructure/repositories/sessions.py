from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.repositories import SessionRepository
from app.domain.sessions import TransferItem, TransferSession
from app.infrastructure.db.mappers import (
    item_to_domain,
    item_to_model,
    session_to_domain,
    session_to_model,
)
from app.infrastructure.db.models import TransferItemModel, TransferSessionModel


class SQLAlchemySessionRepository(SessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, session: TransferSession) -> TransferSession:
        model = session_to_model(session)
        self._session.add(model)
        await self._session.flush()
        return session

    async def save(self, session: TransferSession) -> TransferSession:
        model = session_to_model(session)
        await self._session.merge(model)
        await self._session.flush()
        return session

    async def delete_by_id(self, session_id: UUID) -> None:
        await self._session.execute(delete(TransferSessionModel).where(TransferSessionModel.id == session_id))
        await self._session.flush()

    async def get_by_id(self, session_id: UUID) -> TransferSession | None:
        stmt = (
            select(TransferSessionModel)
            .options(selectinload(TransferSessionModel.items))
            .where(TransferSessionModel.id == session_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return session_to_domain(model) if model is not None else None

    async def get_by_code(self, session_code: str) -> TransferSession | None:
        # Support formatted or unformatted code lookup (e.g. 7431-9285 or 74319285)
        clean_code = session_code.strip().upper()
        stmt = (
            select(TransferSessionModel)
            .options(selectinload(TransferSessionModel.items))
            .where(TransferSessionModel.session_code == clean_code)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return session_to_domain(model) if model is not None else None

    async def list_for_owner(self, owner_id: UUID, limit: int = 50) -> list[TransferSession]:
        stmt = (
            select(TransferSessionModel)
            .options(selectinload(TransferSessionModel.items))
            .where(TransferSessionModel.owner_id == owner_id)
            .order_by(TransferSessionModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [session_to_domain(m) for m in result.scalars().all()]

    async def add_item(self, item: TransferItem) -> TransferItem:
        model = item_to_model(item)
        self._session.add(model)
        await self._session.flush()
        return item

    async def save_item(self, item: TransferItem) -> TransferItem:
        model = item_to_model(item)
        await self._session.merge(model)
        await self._session.flush()
        return item

    async def get_item_by_id(self, item_id: UUID) -> TransferItem | None:
        stmt = select(TransferItemModel).where(TransferItemModel.id == item_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return item_to_domain(model) if model is not None else None

    async def list_expired_before(self, deadline: datetime) -> list[TransferSession]:
        stmt = (
            select(TransferSessionModel)
            .options(selectinload(TransferSessionModel.items))
            .where(TransferSessionModel.expires_at.is_not(None))
            .where(TransferSessionModel.expires_at <= deadline)
            .order_by(TransferSessionModel.expires_at.asc())
        )
        result = await self._session.execute(stmt)
        return [session_to_domain(m) for m in result.scalars().all()]

    async def expire_before(self, deadline: datetime) -> int:
        stmt = (
            delete(TransferSessionModel)
            .where(TransferSessionModel.expires_at.is_not(None))
            .where(TransferSessionModel.expires_at <= deadline)
        )
        result = await self._session.execute(stmt)
        return int(result.rowcount or 0)
