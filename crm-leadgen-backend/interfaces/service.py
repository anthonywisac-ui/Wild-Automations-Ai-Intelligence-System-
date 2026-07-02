# Inspired By: Service layer pattern from TADD
# Feature: Service interfaces for leads, enrichment, scraping, orchestration
# Reason: Clear boundaries for use case implementation
# ============================================================

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID

class BaseService(ABC):
    pass

class LeadServiceProtocol(BaseService):
    @abstractmethod
    async def create_lead(self, data: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    async def get_lead(self, lead_id: UUID) -> Optional[Any]:
        pass

    @abstractmethod
    async def update_lead(self, lead_id: UUID, data: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    async def enrich_lead(self, lead_id: UUID) -> Any:
        pass

    @abstractmethod
    async def score_lead(self, lead_id: UUID) -> float:
        pass

class EnrichmentServiceProtocol(BaseService):
    @abstractmethod
    async def enrich_from_linkedin(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def enrich_from_web(self, url: str) -> Dict[str, Any]:
        pass

class ScrapingServiceProtocol(BaseService):
    @abstractmethod
    async def scrape(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def crawl(self, url: str, depth: int = 1, **kwargs: Any) -> List[Dict[str, Any]]:
        pass

class OrchestrationServiceProtocol(BaseService):
    @abstractmethod
    async def process_lead_workflow(self, lead_id: UUID) -> Dict[str, Any]:
        pass
