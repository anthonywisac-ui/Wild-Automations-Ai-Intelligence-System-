# Inspired By: LangGraph, TADD workflows
# Feature: Orchestration service
# Reason: Coordinate multi-step workflows
# ============================================================

from typing import Dict, Any
from uuid import UUID
from .lead_service import LeadService
from .enrichment_service import EnrichmentService
from .scraping_service import ScrapingService
from ..exceptions import OrchestrationError
from ..logging import get_logger

logger = get_logger(__name__)

class OrchestrationService:
    def __init__(self) -> None:
        self.lead_service = LeadService()
        self.enrichment_service = EnrichmentService()
        self.scraping_service = ScrapingService()

    async def process_lead_workflow(self, lead_id: UUID) -> Dict[str, Any]:
        try:
            logger.info("Starting workflow for lead %s", lead_id)
            await self.enrichment_service.enrich_lead(lead_id)
            score = await self.lead_service.score_lead(lead_id)
            lead = await self.lead_service.get_lead(lead_id)
            logger.info("Workflow completed for lead %s with score %.2f", lead_id, score)
            return {"status": "completed", "lead_id": str(lead_id), "score": score, "lead": lead.model_dump()}
        except Exception as e:
            logger.error("Workflow failed for lead %s: %s", lead_id, e)
            raise OrchestrationError(f"Workflow failed: {e}", cause=e)
