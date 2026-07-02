# Inspired By: crawl4AI plugin architecture
# Repository: https://github.com/unclecode/crawl4AI
# Feature: Plugin base interfaces and registry
# Reason: Extensible plugin system for scrapers, channels, enrichers, etc.
# ============================================================

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type

class BasePlugin(ABC):
    @property
    @abstractmethod
    def plugin_name(self) -> str:
        pass

    @property
    @abstractmethod
    def plugin_version(self) -> str:
        pass

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

class BaseScraperPlugin(BasePlugin, ABC):
    @abstractmethod
    async def extract(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def crawl(self, url: str, depth: int = 1, **kwargs: Any) -> List[Dict[str, Any]]:
        pass

class BaseChannelAdapter(BasePlugin, ABC):
    @abstractmethod
    async def normalize_incoming(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def send_message(self, recipient_id: str, text: str, **kwargs: Any) -> bool:
        pass

class BaseEnricherPlugin(BasePlugin, ABC):
    @abstractmethod
    async def enrich(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def score(self, lead_data: Dict[str, Any]) -> float:
        pass

class BaseAnalyzerPlugin(BasePlugin, ABC):
    @abstractmethod
    async def analyze(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        pass

class BaseLLMPlugin(BasePlugin, ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        pass

class BaseBrowserPlugin(BasePlugin, ABC):
    @abstractmethod
    async def navigate(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        pass

class BaseSearchPlugin(BasePlugin, ABC):
    @abstractmethod
    async def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        pass

class BaseMapsPlugin(BasePlugin, ABC):
    @abstractmethod
    async def geocode(self, address: str) -> Dict[str, Any]:
        pass

class BaseSocialPlugin(BasePlugin, ABC):
    @abstractmethod
    async def get_profile(self, username: str, platform: str) -> Dict[str, Any]:
        pass

class BaseReviewPlugin(BasePlugin, ABC):
    @abstractmethod
    async def get_reviews(self, business_id: str, source: str) -> List[Dict[str, Any]]:
        pass

class BaseCRMPlugin(BasePlugin, ABC):
    @abstractmethod
    async def create_lead(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

class PluginRegistry(ABC):
    @abstractmethod
    def register(self, plugin_class: Type[BasePlugin]) -> None:
        pass

    @abstractmethod
    def get(self, plugin_name: str) -> Optional[Type[BasePlugin]]:
        pass

    @abstractmethod
    def list(self, plugin_type: Optional[Type[BasePlugin]] = None) -> List[Type[BasePlugin]]:
        pass
