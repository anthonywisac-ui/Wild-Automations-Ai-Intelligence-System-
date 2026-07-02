"""
AI Model Registry — tracks all available providers with cost, latency, reliability.
Documented in: docs/AI ARCHITECTURE.md § 1.2

Usage:
    from models.model_registry import ModelRegistry, ModelCapability
    registry = ModelRegistry()
    model = registry.select_model(ModelCapability.RESPONSE_GENERATION)
"""

from enum import Enum
from typing import Dict, List, Optional


class ModelCapability(Enum):
    INTENT_DETECTION = "intent_detection"
    ENTITY_EXTRACTION = "entity_extraction"
    RESPONSE_GENERATION = "response_generation"
    EMBEDDING = "embedding"
    NORMALIZATION = "normalization"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"


class ModelProvider(Enum):
    GEMINI = "gemini"
    CLAUDE = "claude"
    GPT = "gpt"
    GROQ = "groq"
    MISTRAL = "mistral"
    CEREBRAS = "cerebras"
    OLLAMA = "ollama"
    PASSTHROUGH = "passthrough"


class AIModel:
    def __init__(
        self,
        provider: ModelProvider,
        model_name: str,
        capabilities: List[ModelCapability],
        cost_per_token: float,
        context_window: int,
        latency_ms: int,
        reliability: float,
        supported_languages: List[str],
        default_fallback: bool = False,
        env_key: Optional[str] = None,
    ):
        self.provider = provider
        self.model_name = model_name
        self.capabilities = capabilities
        self.cost_per_token = cost_per_token
        self.context_window = context_window
        self.latency_ms = latency_ms
        self.reliability = reliability
        self.supported_languages = supported_languages
        self.default_fallback = default_fallback
        self.env_key = env_key  # env var that must be set for this model to be available
        self.usage_count = 0
        self.total_cost = 0.0

    def is_available(self) -> bool:
        """Check if the model's API key is present in environment."""
        if self.provider in (ModelProvider.OLLAMA, ModelProvider.PASSTHROUGH):
            return True
        if not self.env_key:
            return False
        import os
        return bool(os.environ.get(self.env_key))

    def record_usage(self, tokens: int) -> None:
        self.usage_count += 1
        self.total_cost += tokens * self.cost_per_token

    def __repr__(self) -> str:
        return f"<AIModel provider={self.provider.value} name={self.model_name}>"


class ModelRegistry:
    """
    Central registry of all AI models with capability-based selection.
    Selects cheapest available model that meets capability + reliability threshold.
    """

    def __init__(self):
        self.models: Dict[str, AIModel] = {}
        self._initialize_models()

    def _initialize_models(self) -> None:
        # ── Groq (fastest + very cheap) ──────────────────────────────────────
        self.models["groq-llama3"] = AIModel(
            provider=ModelProvider.GROQ,
            model_name="llama3-8b-8192",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.CLASSIFICATION,
                ModelCapability.SUMMARIZATION,
            ],
            cost_per_token=0.0000001,
            context_window=8192,
            latency_ms=150,
            reliability=0.90,
            supported_languages=["en", "ar"],
            env_key="GROQ_API_KEY",
        )

        self.models["groq-mixtral"] = AIModel(
            provider=ModelProvider.GROQ,
            model_name="mixtral-8x7b-32768",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.CLASSIFICATION,
            ],
            cost_per_token=0.0000005,
            context_window=32768,
            latency_ms=200,
            reliability=0.90,
            supported_languages=["en"],
            env_key="GROQ_API_KEY",
        )

        # ── Cerebras (cheapest overall) ───────────────────────────────────────
        self.models["cerebras-llama3"] = AIModel(
            provider=ModelProvider.CEREBRAS,
            model_name="llama3.1-8b",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.CLASSIFICATION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION,
            ],
            cost_per_token=0.0000001,
            context_window=8192,
            latency_ms=300,
            reliability=0.88,
            supported_languages=["en"],
            default_fallback=True,
            env_key="CEREBRAS_API_KEY",
        )

        # ── Mistral ───────────────────────────────────────────────────────────
        self.models["mistral-large"] = AIModel(
            provider=ModelProvider.MISTRAL,
            model_name="mistral-large-latest",
            capabilities=[
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION,
                ModelCapability.CLASSIFICATION,
                ModelCapability.NORMALIZATION,
            ],
            cost_per_token=0.000002,
            context_window=32000,
            latency_ms=600,
            reliability=0.92,
            supported_languages=["en", "fr", "de", "es"],
            env_key="MISTRAL_API_KEY",
        )

        # ── Gemini ────────────────────────────────────────────────────────────
        self.models["gemini-pro"] = AIModel(
            provider=ModelProvider.GEMINI,
            model_name="gemini-pro",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION,
            ],
            cost_per_token=0.000001,
            context_window=32000,
            latency_ms=800,
            reliability=0.95,
            supported_languages=["en", "ar", "fr", "de", "es"],
            env_key="GEMINI_API_KEY",
        )

        # ── Claude ────────────────────────────────────────────────────────────
        self.models["claude-sonnet"] = AIModel(
            provider=ModelProvider.CLAUDE,
            model_name="claude-sonnet-4-6",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION,
                ModelCapability.NORMALIZATION,
            ],
            cost_per_token=0.000003,
            context_window=200000,
            latency_ms=1200,
            reliability=0.98,
            supported_languages=["en", "ar", "fr", "de", "es"],
            env_key="ANTHROPIC_API_KEY",
        )

        # ── GPT-4o ────────────────────────────────────────────────────────────
        self.models["gpt-4o"] = AIModel(
            provider=ModelProvider.GPT,
            model_name="gpt-4o",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION,
            ],
            cost_per_token=0.000005,
            context_window=128000,
            latency_ms=1000,
            reliability=0.97,
            supported_languages=["en", "ar", "fr", "de", "es"],
            env_key="OPENAI_API_KEY",
        )

        # ── Ollama (offline / free) ───────────────────────────────────────────
        self.models["ollama-mistral"] = AIModel(
            provider=ModelProvider.OLLAMA,
            model_name="mistral",
            capabilities=[
                ModelCapability.INTENT_DETECTION,
                ModelCapability.ENTITY_EXTRACTION,
                ModelCapability.RESPONSE_GENERATION,
                ModelCapability.SUMMARIZATION,
            ],
            cost_per_token=0.0,
            context_window=4096,
            latency_ms=1500,
            reliability=0.80,
            supported_languages=["en"],
        )

        # ── Passthrough (no LLM cost) ─────────────────────────────────────────
        self.models["passthrough"] = AIModel(
            provider=ModelProvider.PASSTHROUGH,
            model_name="passthrough",
            capabilities=[ModelCapability.RESPONSE_GENERATION],
            cost_per_token=0.0,
            context_window=99999,
            latency_ms=0,
            reliability=1.0,
            supported_languages=["en", "ar", "ur"],
            default_fallback=True,
        )

    def select_model(
        self,
        capability: ModelCapability,
        language: str = "en",
        max_tokens: int = 1000,
        max_cost: Optional[float] = None,
        min_reliability: float = 0.85,
    ) -> AIModel:
        """Select cheapest available model that meets all constraints."""
        candidates = [
            m for m in self.models.values()
            if capability in m.capabilities
            and language in m.supported_languages
            and m.reliability >= min_reliability
            and m.context_window >= max_tokens
            and m.is_available()
            and (max_cost is None or m.cost_per_token <= max_cost)
        ]

        if not candidates:
            return self.get_fallback_model(capability)

        # cheapest first
        candidates.sort(key=lambda x: x.cost_per_token)
        return candidates[0]

    def get_fallback_model(self, capability: ModelCapability) -> AIModel:
        """Return first available fallback model for a capability."""
        for m in self.models.values():
            if m.default_fallback and capability in m.capabilities and m.is_available():
                return m
        # try ollama (offline)
        for m in self.models.values():
            if m.provider == ModelProvider.OLLAMA and capability in m.capabilities:
                return m
        # last resort: any
        for m in self.models.values():
            if capability in m.capabilities:
                return m
        raise ValueError(f"No model available for capability: {capability}")

    def get_usage_stats(self) -> Dict[str, Dict]:
        return {
            name: {
                "provider": m.provider.value,
                "usage_count": m.usage_count,
                "total_cost_usd": round(m.total_cost, 6),
            }
            for name, m in self.models.items()
        }

    def available_models(self) -> List[str]:
        return [name for name, m in self.models.items() if m.is_available()]
