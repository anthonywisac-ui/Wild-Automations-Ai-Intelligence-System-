# Inspired By: Lead management use cases
# Feature: Lead service
# Reason: Manage leads, enrichment, scoring
# ============================================================

from typing import Optional, Dict, Any, List
from uuid import UUID
from ..schemas import LeadCreate, LeadUpdate, LeadResponse
from ..repositories import LeadRepository
from ..core.db import get_db_client
from ..exceptions import LeadNotFoundError, ValidationError
from ..logging import get_logger
from ..utils.validators import validate_email

logger = get_logger(__name__)

class LeadService:
    def __init__(self) -> None:
        self.db_client = get_db_client()

    async def create_lead(self, data: Dict[str, Any]) -> LeadResponse:
        if data.get("email") and not validate_email(data["email"]):
            raise ValidationError(f"Invalid email: {data['email']}")
        async with self.db_client.session() as session:
            repo = LeadRepository(session)
            lead = LeadCreate(**data)
            orm_lead = Lead(
                tenant_id=lead.tenant_id,
                name=lead.name,
                email=lead.email,
                phone=lead.phone,
                company=lead.company,
                title=lead.title,
                source=lead.source,
                metadata=lead.metadata,
            )
            saved = await repo.save(orm_lead)
            return LeadResponse.model_validate(saved)

    async def get_lead(self, lead_id: UUID) -> LeadResponse:
        async with self.db_client.session() as session:
            repo = LeadRepository(session)
            lead = await repo.get(lead_id)
            if lead is None:
                raise LeadNotFoundError(f"Lead {lead_id} not found")
            return LeadResponse.model_validate(lead)

    async def update_lead(self, lead_id: UUID, data: Dict[str, Any]) -> LeadResponse:
        async with self.db_client.session() as session:
            repo = LeadRepository(session)
            lead = await repo.get(lead_id)
            if lead is None:
                raise LeadNotFoundError(f"Lead {lead_id} not found")
            update = LeadUpdate(**data)
            for field, value in update.model_dump(exclude_unset=True).items():
                if hasattr(lead, field):
                    setattr(lead, field, value)
            saved = await repo.save(lead)
            return LeadResponse.model_validate(saved)

    async def score_lead(self, lead_id: UUID) -> float:
        async with self.db_client.session() as session:
            repo = LeadRepository(session)
            lead = await repo.get(lead_id)
            if lead is None:
                raise LeadNotFoundError(f"Lead {lead_id} not found")
            score = 50.0
            if lead.title:
                if any(word in lead.title.lower() for word in ["cto", "vp", "director", "head"]):
                    score += 20
                if any(word in lead.title.lower() for word in ["engineer", "architect", "developer"]):
                    score += 10
            if lead.company:
                score += 5
            if lead.email:
                score += 5
            score = min(100.0, score)
            await repo.update_score(lead_id, score)
            logger.info("Scored lead %s: %.2f", lead_id, score)
            return score
