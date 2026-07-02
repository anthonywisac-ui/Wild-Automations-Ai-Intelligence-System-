# Inspired By: crawl4AI, Firecrawl, browser-use
# Repository: https://github.com/unclecode/crawl4AI
# Repository: https://github.com/firecrawl/firecrawl
# Repository: https://github.com/browser-use/browser-use
# Feature: Plugin system for scrapers, channels, enrichers, analyzers, LLMs, etc.
# Reason: Extensible architecture with dynamic loading and lifecycle management
# ============================================================

from .base import BasePlugin, PluginMetadata, PluginConfig, PluginContext
from .registry import PluginRegistry, get_plugin_registry
from .loader import PluginLoader, discover_plugins
from .lifecycle import PluginLifecycleManager
from .context import create_plugin_context, create_dummy_context
from .events import PluginEventEmitter
from .cache import PluginCache, cached
from .retry import with_retry, with_timeout, PluginRetryConfig
from .security import require_scope, validate_api_key, sanitize_input
from .types import ScraperPlugin, AnalyzerPlugin, LLMPlugin, BrowserPlugin, SearchPlugin, MapsPlugin, SocialPlugin, ReviewPlugin, CRMPlugin
from .scrapers import FirecrawlScraper, Crawl4AIScraper
from .channels import TelegramChannel, WhatsAppChannel
from .enrichers import LinkedInEnricher

__all__ = [
    "BasePlugin", "PluginMetadata", "PluginConfig", "PluginContext",
    "PluginRegistry", "get_plugin_registry",
    "PluginLoader", "discover_plugins",
    "PluginLifecycleManager",
    "create_plugin_context", "create_dummy_context",
    "PluginEventEmitter",
    "PluginCache", "cached",
    "with_retry", "with_timeout", "PluginRetryConfig",
    "require_scope", "validate_api_key", "sanitize_input",
    "ScraperPlugin", "AnalyzerPlugin", "LLMPlugin", "BrowserPlugin", "SearchPlugin", "MapsPlugin", "SocialPlugin", "ReviewPlugin", "CRMPlugin",
    "FirecrawlScraper", "Crawl4AIScraper",
    "TelegramChannel", "WhatsAppChannel",
    "LinkedInEnricher",
]
