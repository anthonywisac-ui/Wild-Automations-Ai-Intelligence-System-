# Inspired By: probz_sales, LinkedIn-Scraper
# Feature: Enrichment service
# Reason: Enrich leads with external data
# ============================================================

from typing import Dict, Any
from uuid import UUID
from ..plugins.registry import get_plugin_registry
from ..repositories import LeadRepository
from ..core.db import get_db_client
from ..exceptions import EnrichmentError, LeadNotFoundError
from ..logging import get_logger

logger = get_logger(__name__)

class EnrichmentService:
    def __init__(self) -> None:
        self.db_client = get_db_client()
        self.registry = get_plugin_registry()

    async def enrich_from_linkedin(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        enricher = self.registry.get("linkedin_enricher")
        if enricher is None:
            raise EnrichmentError("LinkedIn enricher not available")
        from ..plugins.context import create_plugin_context
        context = create_plugin_context()
        instance = await self.registry.create_instance("linkedin_enricher", context)
        return await instance.enrich(lead_data)

    async def enrich_lead(self, lead_id: UUID) -> Dict[str, Any]:
        async with self.db_client.session() as session:
            repo = LeadRepository(session)
            lead = await repo.get(lead_id)
            if lead is None:
                raise LeadNotFoundError(f"Lead {lead_id} not found")
            lead_data = {"email": lead.email, "name": lead.name, "company": lead.company, "title": lead.title}
            enriched = await self.enrich_from_linkedin(lead_data)
            lead.enrichment_data.update(enriched.get("enrichment_data", {}))
            await repo.save(lead)
            logger.info("Enriched lead %s", lead_id)
            return lead.enrichment_data
