# Inspired By: Event definitions
# Feature: Concrete event classes
# Reason: Type-safe events
# ============================================================

from typing import Dict, Any
from uuid import UUID
from ..interfaces import Event
from ..schemas.lead import LeadResponse

class LeadCreatedEvent(Event):
    event_type: str = "lead.created"
    source: str = "lead_service"

    def __init__(self, lead: LeadResponse, tenant_id: UUID) -> None:
        super().__init__(
            event_type=self.event_type,
            source=self.source,
            data={"lead_id": str(lead.id), "tenant_id": str(tenant_id), "lead": lead.model_dump()}
        )

class LeadScoredEvent(Event):
    event_type: str = "lead.scored"
    source: str = "lead_service"

    def __init__(self, lead_id: UUID, score: float, tenant_id: UUID) -> None:
        super().__init__(
            event_type=self.event_type,
            source=self.source,
            data={"lead_id": str(lead_id), "tenant_id": str(tenant_id), "score": score}
        )

class LeadEnrichedEvent(Event):
    event_type: str = "lead.enriched"
    source: str = "enrichment_service"

    def __init__(self, lead_id: UUID, tenant_id: UUID, enrichment_data: Dict[str, Any]) -> None:
        super().__init__(
            event_type=self.event_type,
            source=self.source,
            data={"lead_id": str(lead_id), "tenant_id": str(tenant_id), "enrichment_data": enrichment_data}
        )

class ConversationStartedEvent(Event):
    event_type: str = "conversation.started"
    source: str = "agent_orchestrator"

    def __init__(self, conversation_id: UUID, tenant_id: UUID, channel: str) -> None:
        super().__init__(
            event_type=self.event_type,
            source=self.source,
            data={"conversation_id": str(conversation_id), "tenant_id": str(tenant_id), "channel": channel}
        )

class MessageReceivedEvent(Event):
    event_type: str = "message.received"
    source: str = "agent_orchestrator"

    def __init__(self, conversation_id: UUID, sender_id: str, content: str, tenant_id: UUID) -> None:
        super().__init__(
            event_type=self.event_type,
            source=self.source,
            data={"conversation_id": str(conversation_id), "tenant_id": str(tenant_id), "sender_id": sender_id, "content": content}
        )
