# Inspired By: Repository Pattern (Domain-Driven Design)
# Feature: Repository interfaces for leads, tenants, conversations
# Reason: Decouple data access from business logic
# ============================================================

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, TypeVar, Generic
from uuid import UUID

T = TypeVar("T")

class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    async def get(self, id: UUID) -> Optional[T]:
        pass

    @abstractmethod
    async def save(self, entity: T) -> T:
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        pass

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0, **filters: Any) -> List[T]:
        pass

class LeadRepositoryProtocol(ABC):
    @abstractmethod
    async def get_by_email(self, email: str, tenant_id: UUID) -> Optional[Any]:
        pass

    @abstractmethod
    async def search(self, query: str, tenant_id: UUID, limit: int = 20) -> List[Any]:
        pass

    @abstractmethod
    async def update_score(self, lead_id: UUID, score: float) -> Any:
        pass

class TenantRepositoryProtocol(ABC):
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Any]:
        pass

class ConversationRepositoryProtocol(ABC):
    @abstractmethod
    async def get_by_lead(self, lead_id: UUID) -> List[Any]:
        pass
