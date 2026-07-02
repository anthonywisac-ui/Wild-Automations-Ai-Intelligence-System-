# Inspired By: browser-use/browser-use
# Repository: https://github.com/browser-use/browser-use
# Feature: Plugin lifecycle manager
# Reason: Start, stop, health check multiple plugins
# ============================================================

from typing import List, Optional, Dict, Any
import logging
from .registry import get_plugin_registry
from .context import create_plugin_context
from .base import BasePlugin
from ..exceptions import PluginError

logger = logging.getLogger(__name__)

class PluginLifecycleManager:
    def __init__(self) -> None:
        self.registry = get_plugin_registry()
        self._instances: Dict[str, BasePlugin] = {}

    async def start_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None, services: Optional[Dict[str, Any]] = None) -> BasePlugin:
        context = create_plugin_context(plugin_config=config, services=services)
        instance = await self.registry.create_instance(plugin_name, context, config)
        self._instances[plugin_name] = instance
        return instance

    async def start_all(self, plugin_names: Optional[List[str]] = None, configs: Optional[Dict[str, Dict[str, Any]]] = None, services: Optional[Dict[str, Any]] = None) -> List[BasePlugin]:
        if plugin_names is None:
            plugin_names = self.registry.list()
        started = []
        for name in plugin_names:
            try:
                cfg = configs.get(name) if configs else None
                instance = await self.start_plugin(name, cfg, services)
                started.append(instance)
            except Exception as e:
                logger.error("Failed to start plugin %s: %s", name, e)
                raise PluginError(f"Failed to start plugin {name}: {e}", cause=e)
        return started

    async def stop_plugin(self, plugin_name: str) -> None:
        if plugin_name in self._instances:
            await self.registry.stop_instance(plugin_name)
            del self._instances[plugin_name]

    async def stop_all(self) -> None:
        for name in list(self._instances.keys()):
            await self.stop_plugin(name)

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        results = {}
        for name, instance in self._instances.items():
            try:
                results[name] = await instance.health_check()
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        return results

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        return self._instances.get(name)

    def list_running(self) -> List[str]:
        return list(self._instances.keys())
