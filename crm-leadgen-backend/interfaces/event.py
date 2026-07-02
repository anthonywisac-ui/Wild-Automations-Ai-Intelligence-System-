# Inspired By: Event-driven architecture (TADD, Kafka patterns)
# Feature: Event, handler, dispatcher interfaces
# Reason: Decouple event producers from consumers
# ============================================================

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID, uuid4

class Event(BaseModel):
    event_id: UUID = uuid4()
    event_type: str
    timestamp: datetime
    source: str
    data: Dict[str, Any]

class EventHandler(ABC):
    @property
    @abstractmethod
    def event_types(self) -> List[str]:
        pass

    @abstractmethod
    async def handle(self, event: Event) -> None:
        pass

class EventDispatcher(ABC):
    @abstractmethod
    async def dispatch(self, event: Event) -> None:
        pass

    @abstractmethod
    def register(self, handler: EventHandler) -> None:
        pass

    @abstractmethod
    def unregister(self, handler: EventHandler) -> None:
        pass
