# Inspired By: crawl4AI, Firecrawl
# Repository: https://github.com/unclecode/crawl4AI
# Repository: https://github.com/firecrawl/firecrawl
# Feature: Plugin registry with versioning, dependency resolution
# Reason: Manage plugin registration, discovery, and instantiation
# ============================================================

from typing import Type, Optional, List, Dict, Any
import logging
from packaging.version import parse as parse_version

from .base import BasePlugin, PluginMetadata
from ..exceptions import PluginError

logger = logging.getLogger(__name__)

class PluginRegistry:
    def __init__(self) -> None:
        self._plugin_classes: Dict[str, Type[BasePlugin]] = {}
        self._plugin_metadata: Dict[str, PluginMetadata] = {}
        self._plugin_instances: Dict[str, BasePlugin] = {}
        self._by_type: Dict[str, List[str]] = {}
        self._dependencies: Dict[str, List[str]] = {}

    def register(self, plugin_class: Type[BasePlugin]) -> None:
        from .context import create_dummy_context
        dummy_context = create_dummy_context()
        try:
            instance = plugin_class(dummy_context)
            metadata = instance.plugin_metadata
        except Exception as e:
            logger.error("Failed to get metadata for plugin %s: %s", plugin_class.__name__, e)
            raise PluginError(f"Metadata extraction failed: {e}", cause=e)

        name = metadata.name
        version = metadata.version

        if name in self._plugin_classes:
            existing = self._plugin_metadata[name]
            if parse_version(version) < parse_version(existing.version):
                logger.warning("Plugin %s version %s is older than registered %s, skipping", name, version, existing.version)
                return
            elif parse_version(version) == parse_version(existing.version):
                logger.warning("Plugin %s version %s already registered, skipping", name, version)
                return

        self._plugin_classes[name] = plugin_class
        self._plugin_metadata[name] = metadata
        self._dependencies[name] = metadata.dependencies
        self._by_type.setdefault(metadata.plugin_type, []).append(name)
        logger.info("Registered plugin %s version %s (type: %s)", name, version, metadata.plugin_type)

    def get(self, plugin_name: str) -> Optional[Type[BasePlugin]]:
        return self._plugin_classes.get(plugin_name)

    def list(self, plugin_type: Optional[str] = None) -> List[str]:
        if plugin_type is None:
            return list(self._plugin_classes.keys())
        return self._by_type.get(plugin_type, [])

    def get_metadata(self, name: str) -> Optional[PluginMetadata]:
        return self._plugin_metadata.get(name)

    def get_instance(self, name: str) -> Optional[BasePlugin]:
        return self._plugin_instances.get(name)

    async def create_instance(self, name: str, context: Any, config: Optional[Dict[str, Any]] = None) -> BasePlugin:
        plugin_class = self.get(name)
        if plugin_class is None:
            raise PluginError(f"Plugin '{name}' not registered")

        deps = self._dependencies.get(name, [])
        for dep_name in deps:
            if dep_name not in self._plugin_instances:
                await self.create_instance(dep_name, context)

        merged_config = context.config.copy()
        if config:
            merged_config.update(config)
        from .context import PluginContext
        dep_context = PluginContext(config=merged_config, logger=context.logger, cache_client=context.cache, event_dispatcher=context.events, services=context.services)
        instance = plugin_class(dep_context)
        await instance.initialize()
        await instance.start()
        self._plugin_instances[name] = instance
        logger.info("Created and started plugin instance %s", name)
        return instance

    async def stop_instance(self, name: str) -> None:
        instance = self._plugin_instances.get(name)
        if instance:
            await instance.shutdown()
            del self._plugin_instances[name]
            logger.info("Stopped and removed plugin instance %s", name)

    async def stop_all(self) -> None:
        for name in list(self._plugin_instances.keys()):
            await self.stop_instance(name)

    def resolve_dependencies(self, plugin_name: str) -> List[str]:
        visited = set()
        order = []
        def dfs(name: str):
            if name in visited:
                return
            visited.add(name)
            for dep in self._dependencies.get(name, []):
                if dep not in self._plugin_classes:
                    raise PluginError(f"Plugin '{name}' requires '{dep}' which is not registered")
                dfs(dep)
            order.append(name)
        dfs(plugin_name)
        return order

_registry: Optional[PluginRegistry] = None

def get_plugin_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
