# Inspired By: langchain-ai/langgraph, browser-use/browser-use
# Repository: https://github.com/langchain-ai/langgraph
# Repository: https://github.com/browser-use/browser-use
# Feature: Unified exception hierarchy with granular error types
# Reason: Production-grade error classification for observability and recovery
# ============================================================

from .base import PlatformException, ConfigurationError, ValidationError, NotFoundError, ConflictError
from .domain import LeadNotFoundError, LeadAlreadyExistsError, TenantNotFoundError, ConversationNotFoundError, EnrichmentError, ScoringError, OrchestrationError, PluginError
from .infrastructure import DatabaseError, RedisError, ElasticsearchError, ScrapingError, BrowserAutomationError, RateLimitExceededError, ExternalServiceError, NetworkError, TimeoutError
from .api import APIError, AuthenticationError, AuthorizationError, BadRequestError, TooManyRequestsError

__all__ = [
    "PlatformException", "ConfigurationError", "ValidationError", "NotFoundError", "ConflictError",
    "LeadNotFoundError", "LeadAlreadyExistsError", "TenantNotFoundError", "ConversationNotFoundError",
    "EnrichmentError", "ScoringError", "OrchestrationError", "PluginError",
    "DatabaseError", "RedisError", "ElasticsearchError", "ScrapingError", "BrowserAutomationError",
    "RateLimitExceededError", "ExternalServiceError", "NetworkError", "TimeoutError",
    "APIError", "AuthenticationError", "AuthorizationError", "BadRequestError", "TooManyRequestsError",
]
