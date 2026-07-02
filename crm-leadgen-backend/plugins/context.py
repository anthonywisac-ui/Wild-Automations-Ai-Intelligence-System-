# Inspired By: crawl4AI, browser-use
# Repository: https://github.com/unclecode/crawl4AI
# Repository: https://github.com/browser-use/browser-use
# Feature: Plugin context factory and management
# Reason: Provide plugins with necessary dependencies
# ============================================================

from typing import Dict, Any, Optional
import logging
from ..config import get_settings
from ..core.redis import get_redis_client
from ..events.dispatcher import get_event_dispatcher
from ..logging import get_logger

class PluginContext:
    def __init__(self, config: Dict[str, Any], logger: logging.Logger, cache_client: Optional[Any] = None, event_dispatcher: Optional[Any] = None, services: Optional[Dict[str, Any]] = None) -> None:
        self.config = config
        self.logger = logger
        self.cache = cache_client
        self.events = event_dispatcher
        self.services = services or {}
        self.correlation_id: Optional[str] = None

    def get_service(self, name: str) -> Optional[Any]:
        return self.services.get(name)

def create_dummy_context() -> PluginContext:
    settings = get_settings()
    logger = get_logger("dummy_plugin")
    cache = get_redis_client()
    events = get_event_dispatcher()
    return PluginContext(config=settings.model_dump(), logger=logger, cache_client=cache, event_dispatcher=events, services={})

def create_plugin_context(plugin_config: Optional[Dict[str, Any]] = None, services: Optional[Dict[str, Any]] = None) -> PluginContext:
    settings = get_settings()
    logger = get_logger("plugin")
    cache = get_redis_client()
    events = get_event_dispatcher()
    config = settings.model_dump()
    if plugin_config:
        config.update(plugin_config)
    return PluginContext(config=config, logger=logger, cache_client=cache, event_dispatcher=events, services=services or {})
