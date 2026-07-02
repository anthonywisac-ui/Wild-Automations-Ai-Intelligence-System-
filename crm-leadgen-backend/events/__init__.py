# Inspired By: Event-driven architecture
# Feature: Event system
# Reason: Decoupled communication between components
# ============================================================

from .events import LeadCreatedEvent, LeadUpdatedEvent, LeadScoredEvent, LeadEnrichedEvent, ConversationStartedEvent, MessageReceivedEvent
from .dispatcher import EventDispatcher, get_event_dispatcher
from .handlers import LeadScoringHandler, EnrichmentHandler, NotificationHandler

__all__ = [
    "LeadCreatedEvent", "LeadUpdatedEvent", "LeadScoredEvent", "LeadEnrichedEvent",
    "ConversationStartedEvent", "MessageReceivedEvent",
    "EventDispatcher", "get_event_dispatcher",
    "LeadScoringHandler", "EnrichmentHandler", "NotificationHandler",
]
