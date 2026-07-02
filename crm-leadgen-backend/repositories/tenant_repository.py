# Inspired By: Tenant queries
# Feature: Tenant repository
# Reason: Tenant management
# ============================================================

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .base import BaseRepository
from ..models import Tenant
from ..logging import get_logger

logger = get_logger(__name__)

class TenantRepository(BaseRepository[Tenant]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Tenant, session)

    async def get_by_name(self, name: str) -> Optional[Tenant]:
        try:
            stmt = select(Tenant).where(Tenant.name == name)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get tenant by name %s: %s", name, e)
            raise
