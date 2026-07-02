# Inspired By: crawl4AI, Firecrawl
# Repository: https://github.com/unclecode/crawl4AI
# Repository: https://github.com/firecrawl/firecrawl
# Feature: Dynamic plugin discovery from entry points, directories, packages
# Reason: Auto-load plugins without manual registration
# ============================================================

import importlib, pkgutil, sys
from pathlib import Path
from typing import List, Type, Optional
import logging
from importlib.metadata import entry_points

from .base import BasePlugin
from .registry import get_plugin_registry
from ..config import get_settings
from ..exceptions import PluginError

logger = logging.getLogger(__name__)

class PluginLoader:
    def __init__(self) -> None:
        self.registry = get_plugin_registry()
        self.settings = get_settings()

    def discover_from_entry_points(self, group: str = "crm.plugins") -> List[Type[BasePlugin]]:
        discovered = []
        try:
            eps = entry_points(group=group)
            for ep in eps:
                try:
                    plugin_class = ep.load()
                    if issubclass(plugin_class, BasePlugin):
                        self.registry.register(plugin_class)
                        discovered.append(plugin_class)
                        logger.info("Loaded plugin from entry point: %s", ep.name)
                except Exception as e:
                    logger.error("Failed to load entry point %s: %s", ep.name, e)
        except Exception as e:
            logger.warning("Entry point discovery failed: %s", e)
        return discovered

    def discover_from_directories(self, directories: Optional[List[str]] = None) -> List[Type[BasePlugin]]:
        discovered = []
        dirs = directories or self.settings.plugin_dirs
        for dir_path in dirs:
            path = Path(dir_path)
            if not path.exists():
                logger.warning("Plugin directory does not exist: %s", dir_path)
                continue
            if str(path.parent) not in sys.path:
                sys.path.insert(0, str(path.parent))
            package_name = path.name
            try:
                module = importlib.import_module(package_name)
                self._scan_module(module, discovered)
            except ImportError as e:
                logger.warning("Could not import module %s: %s", package_name, e)
                continue
            if hasattr(module, "__path__"):
                for _, subname, is_pkg in pkgutil.iter_modules(module.__path__):
                    if is_pkg:
                        continue
                    try:
                        submodule = importlib.import_module(f"{package_name}.{subname}")
                        self._scan_module(submodule, discovered)
                    except ImportError as e:
                        logger.warning("Could not import submodule %s.%s: %s", package_name, subname, e)
        return discovered

    def _scan_module(self, module, discovered: List) -> None:
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                self.registry.register(attr)
                discovered.append(attr)
                logger.info("Discovered plugin %s in module %s", attr.__name__, module.__name__)

    def discover_from_packages(self, packages: List[str]) -> List[Type[BasePlugin]]:
        discovered = []
        for pkg_name in packages:
            try:
                module = importlib.import_module(pkg_name)
                self._scan_module(module, discovered)
                if hasattr(module, "__path__"):
                    for _, subname, is_pkg in pkgutil.iter_modules(module.__path__):
                        if is_pkg:
                            continue
                        try:
                            submodule = importlib.import_module(f"{pkg_name}.{subname}")
                            self._scan_module(submodule, discovered)
                        except ImportError:
                            pass
            except ImportError as e:
                logger.warning("Could not import package %s: %s", pkg_name, e)
        return discovered

    def load_all(self) -> List[Type[BasePlugin]]:
        discovered = []
        discovered.extend(self.discover_from_entry_points())
        discovered.extend(self.discover_from_directories())
        return discovered

def discover_plugins() -> List[Type[BasePlugin]]:
    loader = PluginLoader()
    return loader.load_all()
