# Inspired By: langchain-ai/langgraph, probz_sales
# Repository: https://github.com/langchain-ai/langgraph
# Feature: Domain-specific exceptions for leads, tenants, conversations, scoring
# Reason: Clear error boundaries at the business logic layer
# ============================================================

from .base import PlatformException


class LeadNotFoundError(PlatformException):
    pass


class LeadAlreadyExistsError(PlatformException):
    pass


class TenantNotFoundError(PlatformException):
    pass


class ConversationNotFoundError(PlatformException):
    pass


class EnrichmentError(PlatformException):
    pass


class ScoringError(PlatformException):
    pass


class OrchestrationError(PlatformException):
    pass


class PluginError(PlatformException):
    pass
