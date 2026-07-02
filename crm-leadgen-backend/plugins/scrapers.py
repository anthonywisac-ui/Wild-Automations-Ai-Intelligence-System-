# Inspired By: Firecrawl, crawl4AI
# Repository: https://github.com/firecrawl/firecrawl
# Repository: https://github.com/unclecode/crawl4AI
# Feature: Concrete scraper plugins using Firecrawl and Crawl4AI
# Reason: Reusable extraction and crawling capabilities
# ============================================================

import logging
from typing import Dict, Any, List
from .base import BasePlugin, PluginMetadata, PluginConfig
from .types import ScraperPlugin
from ..exceptions import ScrapingError
from ..utils.retry import async_retry, RetryConfig

class FirecrawlScraper(ScraperPlugin):
    @property
    def plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(name="firecrawl", version="1.0.0", description="Firecrawl web scraper", author="Firecrawl Team", license="MIT", plugin_type="scraper")

    @property
    def plugin_config(self) -> PluginConfig:
        return PluginConfig(extra={"api_key": ""})

    async def _on_initialize(self) -> None:
        try:
            from firecrawl import FirecrawlApp
            from ..config import get_settings
            settings = get_settings()
            api_key = self.plugin_config.extra.get("api_key") or settings.api_secret_key.get_secret_value()
            self._client = FirecrawlApp(api_key=api_key)
            logging.info("Firecrawl scraper initialized")
        except ImportError:
            self._client = None
            logging.warning("firecrawl-py not installed")

    async def extract(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        if self._client is None:
            raise ScrapingError("Firecrawl client not initialized")
        return await async_retry(self._client.scrape, url, **kwargs)

    async def crawl(self, url: str, depth: int = 1, **kwargs: Any) -> List[Dict[str, Any]]:
        if self._client is None:
            raise ScrapingError("Firecrawl client not initialized")
        return await async_retry(self._client.crawl, url, depth=depth, **kwargs)

class Crawl4AIScraper(ScraperPlugin):
    @property
    def plugin_metadata(self) -> PluginMetadata:
        return PluginMetadata(name="crawl4ai", version="1.0.0", description="Crawl4AI web crawler", author="Crawl4AI Team", license="Apache-2.0", plugin_type="scraper")

    @property
    def plugin_config(self) -> PluginConfig:
        return PluginConfig()

    async def _on_initialize(self) -> None:
        try:
            from crawl4ai import AsyncWebCrawler
            self._crawler = AsyncWebCrawler()
            logging.info("Crawl4AI scraper initialized")
        except ImportError:
            self._crawler = None
            logging.warning("crawl4ai not installed")

    async def extract(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        if self._crawler is None:
            raise ScrapingError("Crawl4AI client not initialized")
        result = await self._crawler.arun(url, **kwargs)
        return {"url": url, "content": result.markdown, "metadata": result.metadata}

    async def crawl(self, url: str, depth: int = 1, **kwargs: Any) -> List[Dict[str, Any]]:
        result = await self.extract(url, **kwargs)
        return [result]
