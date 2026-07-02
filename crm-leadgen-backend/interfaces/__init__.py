# Inspired By: langchain-ai/langgraph, crawl4AI plugin system
# Repository: https://github.com/langchain-ai/langgraph
# Repository: https://github.com/unclecode/crawl4AI
# Feature: Abstract interfaces for plugins, repositories, services, events
# Reason: Enforce Dependency Inversion and provider abstraction
# ============================================================

from .plugin import BasePlugin, BaseScraperPlugin, BaseChannelAdapter, BaseEnricherPlugin, BaseAnalyzerPlugin, BaseLLMPlugin, BaseBrowserPlugin, BaseSearchPlugin, BaseMapsPlugin, BaseSocialPlugin, BaseReviewPlugin, BaseCRMPlugin, PluginRegistry
from .repository import BaseRepository, LeadRepositoryProtocol, TenantRepositoryProtocol, ConversationRepositoryProtocol
from .service import BaseService, LeadServiceProtocol, EnrichmentServiceProtocol, ScrapingServiceProtocol, OrchestrationServiceProtocol
from .event import Event, EventHandler, EventDispatcher

__all__ = [
    "BasePlugin", "BaseScraperPlugin", "BaseChannelAdapter", "BaseEnricherPlugin",
    "BaseAnalyzerPlugin", "BaseLLMPlugin", "BaseBrowserPlugin", "BaseSearchPlugin",
    "BaseMapsPlugin", "BaseSocialPlugin", "BaseReviewPlugin", "BaseCRMPlugin",
    "PluginRegistry",
    "BaseRepository", "LeadRepositoryProtocol", "TenantRepositoryProtocol", "ConversationRepositoryProtocol",
    "BaseService", "LeadServiceProtocol", "EnrichmentServiceProtocol", "ScrapingServiceProtocol", "OrchestrationServiceProtocol",
    "Event", "EventHandler", "EventDispatcher",
]
