# Inspired By: LLM plugin abstraction
# Feature: LLM service
# Reason: Wraps an LLM plugin
# ============================================================

from typing import Optional
from ..plugins.registry import get_plugin_registry
from ..plugins.types import LLMPlugin
from ..exceptions import PluginError
from ..logging import get_logger

logger = get_logger(__name__)

class LLMService:
    def __init__(self, plugin_name: str = "openai_gpt4"):
        self.plugin_name = plugin_name
        self.plugin: Optional[LLMPlugin] = None
        self.registry = get_plugin_registry()

    async def initialize(self) -> None:
        from ..plugins.context import create_plugin_context
        context = create_plugin_context()
        instance = await self.registry.create_instance(self.plugin_name, context)
        self.plugin = instance
        logger.info("LLM service initialized with plugin %s", self.plugin_name)

    async def generate(self, prompt: str, **kwargs) -> str:
        if self.plugin is None:
            raise PluginError("LLM plugin not initialized")
        return await self.plugin.generate(prompt, **kwargs)

    async def shutdown(self) -> None:
        if self.plugin:
            await self.plugin.shutdown()

def get_llm_service(plugin_name: str = "openai_gpt4") -> LLMService:
    return LLMService(plugin_name)
