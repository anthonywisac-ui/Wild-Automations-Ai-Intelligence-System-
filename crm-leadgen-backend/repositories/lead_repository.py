# Inspired By: Lead-specific queries
# Feature: Lead repository with specialised queries
# Reason: Efficient lead retrieval
# ============================================================

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from .base import BaseRepository
from ..models import Lead
from ..exceptions import LeadNotFoundError
from ..logging import get_logger

logger = get_logger(__name__)

class LeadRepository(BaseRepository[Lead]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Lead, session)

    async def get_by_email(self, email: str, tenant_id: UUID) -> Optional[Lead]:
        try:
            stmt = select(Lead).where(Lead.tenant_id == tenant_id, Lead.email == email)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get lead by email %s: %s", email, e)
            raise

    async def search(self, query: str, tenant_id: UUID, limit: int = 20) -> List[Lead]:
        try:
            search_term = f"%{query}%"
            stmt = select(Lead).where(
                Lead.tenant_id == tenant_id,
                or_(
                    Lead.name.ilike(search_term),
                    Lead.company.ilike(search_term),
                    Lead.email.ilike(search_term),
                )
            ).limit(limit)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Failed to search leads for '%s': %s", query, e)
            raise

    async def update_score(self, lead_id: UUID, score: float) -> Lead:
        lead = await self.get(lead_id)
        if lead is None:
            raise LeadNotFoundError(f"Lead {lead_id} not found")
        lead.score = score
        return await self.save(lead)
