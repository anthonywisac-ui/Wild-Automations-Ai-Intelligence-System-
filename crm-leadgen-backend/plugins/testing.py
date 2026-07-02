# Inspired By: testing patterns in crawl4AI, browser-use
# Repository: https://github.com/unclecode/crawl4AI
# Repository: https://github.com/browser-use/browser-use
# Feature: Testing utilities for plugins
# Reason: Simplify plugin unit and integration testing
# ============================================================

from typing import Type, Any, Dict, Optional, List
import asyncio
from .base import BasePlugin, PluginContext
from .registry import get_plugin_registry
from .context import create_dummy_context

class MockPlugin(BasePlugin):
    def __init__(self, context: PluginContext, metadata_override=None, config_override=None):
        super().__init__(context)
        self._metadata = metadata_override or self.plugin_metadata
        self._config = config_override or self.plugin_config

    @property
    def plugin_metadata(self):
        return self._metadata

    @property
    def plugin_config(self):
        return self._config

def create_test_plugin_context(config_override: Optional[Dict[str, Any]] = None, services: Optional[Dict[str, Any]] = None) -> PluginContext:
    base_context = create_dummy_context()
    if config_override:
        base_context.config.update(config_override)
    if services:
        base_context.services.update(services)
    return base_context

async def run_plugin_lifecycle(plugin: BasePlugin) -> None:
    await plugin.initialize()
    await plugin.start()
    await plugin.stop()
    await plugin.shutdown()

def assert_plugin_healthy(plugin: BasePlugin) -> None:
    health = asyncio.run(plugin.health_check())
    assert health.get("status") == "ok", f"Plugin not healthy: {health}"
