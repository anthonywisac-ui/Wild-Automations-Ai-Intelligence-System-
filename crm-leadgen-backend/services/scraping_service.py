# Inspired By: Firecrawl, crawl4AI
# Feature: Scraping service
# Reason: Abstract web scraping
# ============================================================

from typing import Dict, Any, List
from ..plugins.registry import get_plugin_registry
from ..exceptions import ScrapingError
from ..logging import get_logger

logger = get_logger(__name__)

class ScrapingService:
    def __init__(self, scraper_name: str = "firecrawl") -> None:
        self.registry = get_plugin_registry()
        self.scraper_name = scraper_name

    async def _get_scraper(self):
        from ..plugins.context import create_plugin_context
        context = create_plugin_context()
        instance = await self.registry.create_instance(self.scraper_name, context)
        return instance

    async def scrape(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        scraper = await self._get_scraper()
        try:
            return await scraper.extract(url, **kwargs)
        except Exception as e:
            raise ScrapingError(f"Scraping failed: {e}", cause=e)

    async def crawl(self, url: str, depth: int = 1, **kwargs: Any) -> List[Dict[str, Any]]:
        scraper = await self._get_scraper()
        try:
            return await scraper.crawl(url, depth=depth, **kwargs)
        except Exception as e:
            raise ScrapingError(f"Crawling failed: {e}", cause=e)
