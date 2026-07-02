# Inspired By: crawl4AI, browser-use
# Repository: https://github.com/unclecode/crawl4AI
# Repository: https://github.com/browser-use/browser-use
# Feature: Base plugin with metadata, config, lifecycle, health
# Reason: Common foundation for all plugin types
# ============================================================

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class PluginMetadata(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    plugin_type: str

class PluginConfig(BaseModel):
    enabled: bool = True
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    log_level: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

class PluginContext:
    def __init__(self, config: Dict[str, Any], logger: Any, cache_client: Optional[Any] = None, event_dispatcher: Optional[Any] = None, services: Optional[Dict[str, Any]] = None) -> None:
        self.config = config
        self.logger = logger
        self.cache = cache_client
        self.events = event_dispatcher
        self.services = services or {}
        self.correlation_id: Optional[str] = None

    def get_service(self, name: str) -> Optional[Any]:
        return self.services.get(name)

class BasePlugin(ABC):
    def __init__(self, context: PluginContext) -> None:
        self.context = context
        self._logger = context.logger
        self._state = "created"
        self._started_at: Optional[datetime] = None
        self._health_status: Dict[str, Any] = {"status": "unknown"}

    @property
    @abstractmethod
    def plugin_metadata(self) -> PluginMetadata:
        pass

    @property
    @abstractmethod
    def plugin_config(self) -> PluginConfig:
        pass

    @property
    def state(self) -> str:
        return self._state

    async def initialize(self) -> None:
        self._state = "initializing"
        try:
            await self._on_initialize()
            self._state = "initialized"
            self._logger.info("Plugin %s initialized", self.plugin_metadata.name)
        except Exception as e:
            self._state = "error"
            raise

    async def _on_initialize(self) -> None:
        pass

    async def start(self) -> None:
        if self._state not in ("initialized", "stopped"):
            raise RuntimeError(f"Cannot start plugin in state {self._state}")
        self._state = "starting"
        try:
            await self._on_start()
            self._state = "running"
            self._started_at = datetime.utcnow()
            self._logger.info("Plugin %s started", self.plugin_metadata.name)
        except Exception as e:
            self._state = "error"
            raise

    async def _on_start(self) -> None:
        pass

    async def stop(self) -> None:
        if self._state not in ("running", "error"):
            return
        self._state = "stopping"
        try:
            await self._on_stop()
            self._state = "stopped"
            self._logger.info("Plugin %s stopped", self.plugin_metadata.name)
        except Exception as e:
            self._state = "error"
            raise

    async def _on_stop(self) -> None:
        pass

    async def shutdown(self) -> None:
        await self.stop()
        try:
            await self._on_shutdown()
            self._state = "shutdown"
            self._logger.info("Plugin %s shut down", self.plugin_metadata.name)
        except Exception as e:
            raise

    async def _on_shutdown(self) -> None:
        pass

    async def health_check(self) -> Dict[str, Any]:
        try:
            result = await self._health_check()
            self._health_status = result
            return result
        except Exception as e:
            self._health_status = {"status": "unhealthy", "error": str(e)}
            return self._health_status

    async def _health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "state": self._state}
