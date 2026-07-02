# Inspired By: Event handlers
# Feature: Concrete event handlers
# Reason: React to events
# ============================================================

from typing import List
from ..interfaces import EventHandler, Event
from ..services.lead_service import LeadService
from ..services.enrichment_service import EnrichmentService
from ..logging import get_logger
from .events import LeadCreatedEvent, LeadScoredEvent

logger = get_logger(__name__)

class LeadScoringHandler(EventHandler):
    event_types = ["lead.created"]

    def __init__(self) -> None:
        self.lead_service = LeadService()

    async def handle(self, event: Event) -> None:
        lead_id = event.data.get("lead_id")
        if lead_id:
            try:
                score = await self.lead_service.score_lead(lead_id)
                logger.info("Auto-scored lead %s: %.2f", lead_id, score)
            except Exception as e:
                logger.error("Auto-scoring failed for lead %s: %s", lead_id, e)

class EnrichmentHandler(EventHandler):
    event_types = ["lead.created"]

    def __init__(self) -> None:
        self.enrichment_service = EnrichmentService()

    async def handle(self, event: Event) -> None:
        lead_id = event.data.get("lead_id")
        if lead_id:
            try:
                await self.enrichment_service.enrich_lead(lead_id)
                logger.info("Auto-enriched lead %s", lead_id)
            except Exception as e:
                logger.error("Auto-enrichment failed for lead %s: %s", lead_id, e)

class NotificationHandler(EventHandler):
    event_types = ["lead.scored"]

    async def handle(self, event: Event) -> None:
        lead_id = event.data.get("lead_id")
        score = event.data.get("score")
        if lead_id and score is not None:
            if score >= 80:
                logger.info("🔥 High-value lead %s scored %.2f", lead_id, score)
            else:
                logger.info("Lead %s scored %.2f", lead_id, score)
