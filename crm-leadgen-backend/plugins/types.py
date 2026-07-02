# Inspired By: crawl4AI, Firecrawl, browser-use
# Feature: Specialised plugin interfaces for each domain
# Reason: Type‑safe contracts for different plugin categories
# ============================================================

from abc import abstractmethod
from typing import Dict, Any, List
from .base import BasePlugin

class ScraperPlugin(BasePlugin):
    @abstractmethod
    async def extract(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def crawl(self, url: str, depth: int = 1, **kwargs: Any) -> List[Dict[str, Any]]:
        pass

class AnalyzerPlugin(BasePlugin):
    @abstractmethod
    async def analyze(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        pass

class LLMPlugin(BasePlugin):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        pass

class BrowserPlugin(BasePlugin):
    @abstractmethod
    async def navigate(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        pass

class SearchPlugin(BasePlugin):
    @abstractmethod
    async def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        pass

class MapsPlugin(BasePlugin):
    @abstractmethod
    async def geocode(self, address: str) -> Dict[str, Any]:
        pass

class SocialPlugin(BasePlugin):
    @abstractmethod
    async def get_profile(self, username: str, platform: str) -> Dict[str, Any]:
        pass

class ReviewPlugin(BasePlugin):
    @abstractmethod
    async def get_reviews(self, business_id: str, source: str) -> List[Dict[str, Any]]:
        pass

class CRMPlugin(BasePlugin):
    @abstractmethod
    async def create_lead(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

__all__ = [
    "ScraperPlugin", "AnalyzerPlugin", "LLMPlugin", "BrowserPlugin",
    "SearchPlugin", "MapsPlugin", "SocialPlugin", "ReviewPlugin", "CRMPlugin",
]
