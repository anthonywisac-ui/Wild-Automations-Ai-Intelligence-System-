# Inspired By: Repository Pattern
# Feature: Base repository with CRUD operations
# Reason: Common data access methods
# ============================================================

from typing import Optional, List, Type, Dict, Any, Generic, TypeVar
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from ..core.db import Base
from ..exceptions import DatabaseError
from ..logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    def __init__(self, model_class: Type[T], session: AsyncSession) -> None:
        self.model_class = model_class
        self.session = session
        self.logger = logger.bind(model=model_class.__name__)

    async def get(self, id: UUID) -> Optional[T]:
        try:
            stmt = select(self.model_class).where(self.model_class.id == id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Get failed: {e}", cause=e)

    async def save(self, entity: T) -> T:
        try:
            self.session.add(entity)
            await self.session.flush()
            await self.session.refresh(entity)
            return entity
        except Exception as e:
            raise DatabaseError(f"Save failed: {e}", cause=e)

    async def delete(self, id: UUID) -> bool:
        try:
            stmt = delete(self.model_class).where(self.model_class.id == id)
            result = await self.session.execute(stmt)
            await self.session.flush()
            return result.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Delete failed: {e}", cause=e)

    async def list(self, limit: int = 100, offset: int = 0, **filters: Any) -> List[T]:
        try:
            stmt = select(self.model_class)
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)
            stmt = stmt.limit(limit).offset(offset)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"List failed: {e}", cause=e)

    async def count(self, **filters: Any) -> int:
        try:
            stmt = select(func.count()).select_from(self.model_class)
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            raise DatabaseError(f"Count failed: {e}", cause=e)
