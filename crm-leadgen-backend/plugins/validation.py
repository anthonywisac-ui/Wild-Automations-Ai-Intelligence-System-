# Inspired By: crawl4AI plugin validation
# Repository: https://github.com/unclecode/crawl4AI
# Feature: Plugin class and config validation
# Reason: Ensure plugins meet required contracts before loading
# ============================================================

from typing import Type, Dict, Any, Optional
import logging
from pydantic import ValidationError
from .base import BasePlugin, PluginMetadata, PluginConfig
from ..exceptions import PluginError, ConfigurationError

logger = logging.getLogger(__name__)

def validate_plugin_class(plugin_class: Type[BasePlugin]) -> bool:
    if not isinstance(plugin_class, type) or not issubclass(plugin_class, BasePlugin):
        raise PluginError(f"{plugin_class} is not a subclass of BasePlugin")

    from .context import create_dummy_context
    context = create_dummy_context()
    try:
        instance = plugin_class(context)
        metadata = instance.plugin_metadata
        config = instance.plugin_config
    except Exception as e:
        raise PluginError(f"Failed to instantiate plugin {plugin_class.__name__}: {e}", cause=e)

    if not isinstance(metadata, PluginMetadata):
        raise PluginError(f"plugin_metadata must be PluginMetadata, got {type(metadata)}")
    if not metadata.name or not metadata.version:
        raise PluginError("plugin_metadata.name and version are required")
    if not isinstance(config, PluginConfig):
        raise PluginError(f"plugin_config must be PluginConfig, got {type(config)}")
    return True

def validate_plugin_config(plugin_name: str, config_data: Dict[str, Any], config_class: Optional[Type[PluginConfig]] = None) -> PluginConfig:
    config_cls = config_class or PluginConfig
    try:
        return config_cls(**config_data)
    except ValidationError as e:
        raise ConfigurationError(f"Invalid config for plugin {plugin_name}: {e}", details=e.errors())
    except Exception as e:
        raise ConfigurationError(f"Config validation failed for {plugin_name}: {e}", cause=e)

def validate_plugin_dependencies(plugin_name: str, dependencies: list, registry) -> bool:
    missing = []
    for dep in dependencies:
        if dep not in registry._plugin_classes:
            missing.append(dep)
    if missing:
        raise PluginError(f"Plugin {plugin_name} has unresolved dependencies: {missing}")
    return True
