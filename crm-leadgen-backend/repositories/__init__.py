# Inspired By: Repository Pattern
# Feature: Repository implementations
# Reason: Data access layer
# ============================================================

from .base import BaseRepository
from .lead_repository import LeadRepository
from .tenant_repository import TenantRepository
from .conversation_repository import ConversationRepository

__all__ = ["BaseRepository", "LeadRepository", "TenantRepository", "ConversationRepository"]
