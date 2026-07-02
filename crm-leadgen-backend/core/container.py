# Inspired By: browser-use/browser-use (DI pattern)
# Repository: https://github.com/browser-use/browser-use
# Feature: Simple dependency injection container
# Reason: Manage service lifetimes and resolve dependencies
# ============================================================

from typing import Any, Dict, Type, Callable, Optional
import logging

logger = logging.getLogger(__name__)

class Container:
    _instance: Optional["Container"] = None

    def __new__(cls) -> "Container":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._singletons: Dict[Type, Any] = {}
            cls._instance._factories: Dict[Type, Callable] = {}
        return cls._instance

    def register(self, interface: Type, implementation: Any, singleton: bool = True) -> None:
        if singleton:
            self._singletons[interface] = implementation
        else:
            self._factories[interface] = implementation
        logger.debug("Registered %s -> %s (singleton=%s)", interface.__name__, implementation.__name__, singleton)

    def register_instance(self, interface: Type, instance: Any) -> None:
        self._singletons[interface] = instance

    def resolve(self, interface: Type) -> Any:
        if interface in self._singletons:
            return self._singletons[interface]
        if interface in self._factories:
            instance = self._factories[interface]()
            self._singletons[interface] = instance
            return instance
        raise KeyError(f"No implementation registered for {interface.__name__}")

    def clear(self) -> None:
        self._singletons.clear()
        self._factories.clear()

_container: Optional[Container] = None

def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container
